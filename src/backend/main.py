"""Main FastAPI application."""
from fastapi import FastAPI, HTTPException, Header, Depends, UploadFile, File
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from contextlib import asynccontextmanager
import time

from config import settings
from database import db
from vector_store import vector_store, SecurityException
from llm_service import llm_service
from cache_service import cache_service


# Pydantic models
class TenantContext(BaseModel):
    """Tenant context from authentication."""
    tenant_id: str
    tenant_name: str


class DocumentUploadResponse(BaseModel):
    """Response for document upload."""
    document_id: str
    name: str
    chunks_count: int
    message: str


class QueryRequest(BaseModel):
    """Request for querying the knowledge base."""
    question: str = Field(..., min_length=1, max_length=1000)


class Source(BaseModel):
    """Source document reference."""
    document_name: str
    relevant_excerpt: str


class QueryResponse(BaseModel):
    """Response for query."""
    answer: Optional[str]
    sources: List[Source]
    confidence: Optional[float]
    insufficient_context: bool
    processing_time_ms: int
    cached: bool = False


class DocumentListItem(BaseModel):
    """Document list item."""
    id: str
    name: str
    content_type: str
    uploaded_at: str


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    services: Dict[str, str]


# Application lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown."""
    # Startup
    await db.connect()
    await cache_service.connect()
    yield
    # Shutdown
    await db.disconnect()
    await cache_service.disconnect()


# Create FastAPI app
app = FastAPI(
    title="AI Knowledge Assistant",
    description="Internal knowledge assistant with RAG",
    version="1.0.0",
    lifespan=lifespan
)


# Authentication dependency
async def get_tenant_context(
    x_api_key: str = Header(..., alias="X-API-Key")
) -> TenantContext:
    """Extract and validate tenant from API key."""
    # For MVP, use simple API key hash matching
    tenant = await db.get_tenant_by_api_key(x_api_key)
    
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not tenant['is_active']:
        raise HTTPException(status_code=403, detail="Tenant account inactive")
    
    return TenantContext(
        tenant_id=str(tenant['id']),
        tenant_name=tenant['name']
    )


# Health check endpoint
@app.get("/api/v1/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    services = {
        "api": "healthy",
        "database": "unknown",
        "redis": "unknown",
        "qdrant": "unknown"
    }
    
    # Check database
    try:
        async with db.pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        services["database"] = "healthy"
    except Exception:
        services["database"] = "unhealthy"
    
    # Check Redis
    try:
        await cache_service.redis.ping()
        services["redis"] = "healthy"
    except Exception:
        services["redis"] = "unhealthy"
    
    # Check Qdrant
    try:
        vector_store.client.get_collections()
        services["qdrant"] = "healthy"
    except Exception:
        services["qdrant"] = "unhealthy"
    
    overall_status = "healthy" if all(
        s == "healthy" for s in services.values()
    ) else "degraded"
    
    return HealthResponse(status=overall_status, services=services)


# Document upload endpoint
@app.post("/api/v1/documents", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    context: TenantContext = Depends(get_tenant_context)
):
    """Upload a document to the knowledge base."""
    # Read file content
    content = await file.read()
    text = content.decode('utf-8')
    
    # Create document in database
    document_id = await db.create_document(
        tenant_id=context.tenant_id,
        name=file.filename,
        content=text,
        content_type=file.content_type or "text/markdown"
    )
    
    # Chunk document
    chunks = llm_service.chunk_text(text)
    
    # Generate embeddings
    chunks_with_embeddings = await llm_service.embed_chunks(chunks)
    
    # Store in vector database
    await vector_store.store_chunks(
        tenant_id=context.tenant_id,
        document_id=document_id,
        document_name=file.filename,
        chunks=chunks_with_embeddings
    )
    
    # Audit log
    await db.create_audit_log(
        tenant_id=context.tenant_id,
        action="document_upload",
        resource_type="document",
        resource_id=document_id,
        metadata={"name": file.filename, "chunks": len(chunks)}
    )
    
    return DocumentUploadResponse(
        document_id=document_id,
        name=file.filename,
        chunks_count=len(chunks),
        message=f"Document uploaded successfully with {len(chunks)} chunks"
    )


# Query endpoint
@app.post("/api/v1/query", response_model=QueryResponse)
async def query_knowledge_base(
    request: QueryRequest,
    context: TenantContext = Depends(get_tenant_context)
):
    """Query the knowledge base."""
    start_time = time.time()
    
    # Check rate limit
    if not await cache_service.check_rate_limit(context.tenant_id):
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded: {settings.queries_per_minute} queries per minute"
        )
    
    # Generate question embedding
    question_embedding = await llm_service.embed_text(request.question)
    
    # Search vector database
    try:
        chunks = await vector_store.search(
            tenant_id=context.tenant_id,
            query_vector=question_embedding,
            top_k=settings.top_k_chunks,
            score_threshold=settings.similarity_threshold
        )
    except SecurityException as e:
        # Critical security violation
        await db.create_audit_log(
            tenant_id=context.tenant_id,
            action="security_violation",
            resource_type="query",
            metadata={"error": str(e), "question": request.question}
        )
        raise HTTPException(status_code=500, detail="Security violation detected")
    
    # Check cache
    chunk_ids = [c['document_id'] for c in chunks]
    cached_response = await cache_service.get_cached_response(
        tenant_id=context.tenant_id,
        question=request.question,
        chunk_ids=chunk_ids
    )
    
    if cached_response:
        processing_time = int((time.time() - start_time) * 1000)
        return QueryResponse(
            answer=cached_response.get('answer'),
            sources=[Source(**s) for s in cached_response.get('sources', [])],
            confidence=cached_response.get('confidence'),
            insufficient_context=cached_response.get('insufficient_context', False),
            processing_time_ms=processing_time,
            cached=True
        )
    
    # If no chunks found, return insufficient context
    if not chunks:
        result = {
            'answer': None,
            'sources': [],
            'confidence': 0.0,
            'insufficient_context': True
        }
    else:
        # Generate answer with LLM
        result = await llm_service.generate_answer(
            question=request.question,
            context_chunks=chunks,
            tenant_name=context.tenant_name
        )
    
    # Extract token usage
    tokens = result.pop('_tokens', {})
    
    # Cache response
    await cache_service.cache_response(
        tenant_id=context.tenant_id,
        question=request.question,
        chunk_ids=chunk_ids,
        response=result
    )
    
    # Calculate processing time
    processing_time = int((time.time() - start_time) * 1000)
    
    # Log query
    await db.create_query_log(
        tenant_id=context.tenant_id,
        question=request.question,
        answer=result.get('answer'),
        sources=result.get('sources', []),
        confidence=result.get('confidence'),
        insufficient_context=result.get('insufficient_context', False),
        retrieved_chunks_count=len(chunks),
        llm_tokens_used=tokens.get('total', 0),
        processing_time_ms=processing_time
    )
    
    # Audit log
    await db.create_audit_log(
        tenant_id=context.tenant_id,
        action="query_execute",
        resource_type="query",
        metadata={
            "question": request.question,
            "chunks_retrieved": len(chunks),
            "insufficient_context": result.get('insufficient_context', False)
        }
    )
    
    return QueryResponse(
        answer=result.get('answer'),
        sources=[Source(**s) for s in result.get('sources', [])],
        confidence=result.get('confidence'),
        insufficient_context=result.get('insufficient_context', False),
        processing_time_ms=processing_time,
        cached=False
    )


# List documents endpoint
@app.get("/api/v1/documents", response_model=List[DocumentListItem])
async def list_documents(
    context: TenantContext = Depends(get_tenant_context)
):
    """List all documents for the tenant."""
    documents = await db.list_documents(context.tenant_id)
    
    return [
        DocumentListItem(
            id=str(doc['id']),
            name=doc['name'],
            content_type=doc['content_type'],
            uploaded_at=doc['uploaded_at'].isoformat()
        )
        for doc in documents
    ]


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "AI Knowledge Assistant API",
        "version": "1.0.0",
        "docs": "/docs"
    }