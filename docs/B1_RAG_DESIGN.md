# B1. RAG Design

## Document Chunking Strategy

### Chunking Parameters
- **Chunk Size**: 500 tokens (~375 words)
- **Overlap**: 50 tokens between consecutive chunks
- **Method**: Semantic chunking with sentence boundary preservation

### Why These Parameters?

**500-token chunks** balance context and precision:
- Large enough to contain complete thoughts and context
- Small enough to fit multiple chunks in the LLM context window (8k tokens)
- Aligns with typical paragraph/section length in business documents

**50-token overlap** prevents information loss:
- Ensures sentences spanning chunk boundaries are captured in both chunks
- Improves retrieval recall for queries matching boundary content
- Minimal storage overhead (~10% increase)

### Chunking Implementation
```python
def chunk_document(text: str, chunk_size: int = 500, overlap: int = 50):
    # Tokenize document
    tokens = tokenizer.encode(text)
    chunks = []
    
    for i in range(0, len(tokens), chunk_size - overlap):
        chunk_tokens = tokens[i:i + chunk_size]
        chunk_text = tokenizer.decode(chunk_tokens)
        
        # Preserve sentence boundaries
        if i + chunk_size < len(tokens):
            # Find last complete sentence
            last_period = chunk_text.rfind('.')
            if last_period > chunk_size * 0.7:  # At least 70% of chunk
                chunk_text = chunk_text[:last_period + 1]
        
        chunks.append({
            "text": chunk_text,
            "index": len(chunks),
            "token_count": len(chunk_tokens)
        })
    
    return chunks
```

## Embedding Storage

### Vector Database: Qdrant
- **Embedding Model**: `text-embedding-3-small` (1536 dimensions)
- **Distance Metric**: Cosine similarity
- **Index Type**: HNSW (Hierarchical Navigable Small World) for fast approximate search

### Storage Schema
```python
# Each chunk stored as a point in Qdrant
{
    "id": "uuid",
    "vector": [0.123, -0.456, ...],  # 1536 dimensions
    "payload": {
        "tenant_id": "tenant-uuid",
        "document_id": "doc-uuid",
        "document_name": "Employee Handbook.md",
        "chunk_text": "Full text of chunk...",
        "chunk_index": 0,
        "total_chunks": 15,
        "uploaded_at": "2024-01-15T10:30:00Z",
        "metadata": {
            "document_type": "policy",
            "department": "HR"
        }
    }
}
```

### Why Qdrant?
- **Performance**: Fast vector search with HNSW index
- **Filtering**: Native support for metadata filtering (tenant_id, document_type)
- **Scalability**: Handles millions of vectors efficiently
- **Docker Support**: Easy deployment via Docker Compose

## Retrieval Process

### Query Flow
1. **Query Embedding**: Convert user question to 1536-dimensional vector using same embedding model
2. **Similarity Search**: Search Qdrant collection for top-k most similar chunks
3. **Filtering**: Apply tenant_id filter to enforce isolation
4. **Ranking**: Qdrant returns chunks ranked by cosine similarity score
5. **Context Assembly**: Combine top 5 chunks into prompt context

### Retrieval Parameters
```python
search_params = {
    "collection_name": f"tenant_{tenant_id}_documents",
    "query_vector": question_embedding,
    "limit": 5,  # Top 5 chunks
    "score_threshold": 0.7,  # Minimum similarity score
    "filter": {
        "must": [
            {"key": "tenant_id", "match": {"value": tenant_id}}
        ]
    }
}
```

### Why Top-5 Chunks?
- **Context Window**: 5 chunks × 500 tokens = 2,500 tokens, leaving ~5,000 tokens for question + answer
- **Diversity**: Multiple chunks increase chance of covering all relevant information
- **Diminishing Returns**: Chunks beyond top-5 typically have low relevance scores

### Score Threshold (0.7)
- **Quality Filter**: Rejects chunks with low semantic similarity
- **Prevents Noise**: Avoids including irrelevant context that confuses the LLM
- **Insufficient Context Detection**: If no chunks meet threshold, trigger `insufficient_context` response

## Tenant Filtering Strategy

### Multi-Layer Isolation

**Layer 1: Collection Separation**
- Each tenant has dedicated Qdrant collection: `tenant_{tenant_id}_documents`
- Physical isolation at storage level
- Zero chance of cross-tenant data leakage via search

**Layer 2: Metadata Filtering**
- Even within tenant-specific collections, all searches include tenant_id filter
- Defense-in-depth: protects against collection naming bugs or misconfigurations

**Layer 3: Application Validation**
- Service layer validates tenant_id from authentication before any database operation
- Prevents injection attacks or API key confusion

### Implementation Example
```python
async def search_documents(
    question: str,
    tenant_id: str,
    top_k: int = 5
) -> List[SearchResult]:
    # Generate question embedding
    question_embedding = await embedding_service.embed(question)
    
    # Search in tenant-specific collection
    collection_name = f"tenant_{tenant_id}_documents"
    
    results = await qdrant_client.search(
        collection_name=collection_name,
        query_vector=question_embedding,
        limit=top_k,
        score_threshold=0.7,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="tenant_id",
                    match=MatchValue(value=tenant_id)
                )
            ]
        )
    )
    
    return results
```

### Tenant Isolation Guarantees

1. **Collection-level isolation**: Impossible to accidentally search another tenant's collection
2. **Filter-level safety**: Redundant tenant_id filter catches any collection naming errors
3. **Audit trail**: All searches logged with tenant_id for compliance review
4. **Access control**: API keys are tenant-specific and validated before any operation

## Retrieval Quality Optimization

### Hybrid Search (Future Enhancement)
Combine vector search with keyword search for better recall:
- **Vector Search**: Captures semantic similarity
- **Keyword Search**: Ensures exact term matches (e.g., policy numbers, product names)
- **Fusion**: Combine results using Reciprocal Rank Fusion (RRF)

### Re-ranking (Future Enhancement)
After initial retrieval, re-rank chunks using:
- **Cross-encoder model**: More accurate but slower similarity scoring
- **Metadata signals**: Boost recently updated documents or high-authority sources

### Query Expansion (Future Enhancement)
Generate multiple query variations to improve recall:
- Synonyms: "remote work" → "work from home", "telecommuting"
- Specificity levels: "expense policy" → "travel expense reimbursement policy"