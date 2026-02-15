"""Vector database operations using Qdrant."""
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct,
    Filter, FieldCondition, MatchValue
)
from config import settings
import uuid


class VectorStore:
    """Qdrant vector database manager."""
    
    def __init__(self):
        self.client = QdrantClient(url=settings.qdrant_url)
    
    def _get_collection_name(self, tenant_id: str) -> str:
        """Get collection name for tenant."""
        # Remove hyphens from UUID for cleaner collection names
        clean_id = tenant_id.replace('-', '')[:16]
        return f"tenant_{clean_id}_documents"
    
    async def ensure_collection(self, tenant_id: str):
        """Create collection if it doesn't exist."""
        collection_name = self._get_collection_name(tenant_id)
        
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=1536,  # text-embedding-3-small dimension
                    distance=Distance.COSINE
                )
            )
            
            # Create payload index for tenant_id filtering
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name="tenant_id",
                field_schema="keyword"
            )
    
    async def store_chunks(
        self,
        tenant_id: str,
        document_id: str,
        document_name: str,
        chunks: List[Dict[str, Any]]
    ):
        """Store document chunks with embeddings."""
        collection_name = self._get_collection_name(tenant_id)
        await self.ensure_collection(tenant_id)
        
        points = []
        for chunk in chunks:
            point = PointStruct(
                id=str(uuid.uuid4()),
                vector=chunk['embedding'],
                payload={
                    'tenant_id': tenant_id,
                    'document_id': document_id,
                    'document_name': document_name,
                    'chunk_text': chunk['text'],
                    'chunk_index': chunk['index'],
                    'total_chunks': len(chunks),
                    'token_count': chunk['token_count']
                }
            )
            points.append(point)
        
        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
    
    async def search(
        self,
        tenant_id: str,
        query_vector: List[float],
        top_k: int = 5,
        score_threshold: float = 0.7
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks."""
        collection_name = self._get_collection_name(tenant_id)
        
        # Check if collection exists
        collections = self.client.get_collections().collections
        collection_names = [c.name for c in collections]
        
        if collection_name not in collection_names:
            return []
        
        # Search with tenant filter
        results = self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k,
            score_threshold=score_threshold,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="tenant_id",
                        match=MatchValue(value=tenant_id)
                    )
                ]
            )
        )
        
        # Validate tenant isolation
        chunks = []
        for result in results:
            # Security check: verify tenant_id
            if result.payload.get('tenant_id') != tenant_id:
                raise SecurityException(f"Tenant isolation violation detected")
            
            chunks.append({
                'document_id': result.payload['document_id'],
                'document_name': result.payload['document_name'],
                'chunk_text': result.payload['chunk_text'],
                'chunk_index': result.payload['chunk_index'],
                'score': result.score
            })
        
        return chunks


class SecurityException(Exception):
    """Security violation exception."""
    pass


# Global vector store instance
vector_store = VectorStore()