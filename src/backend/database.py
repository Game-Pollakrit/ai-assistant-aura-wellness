"""Database connection and models."""
import asyncpg
from typing import Optional, List, Dict, Any
from datetime import datetime
from config import settings


class Database:
    """Database connection manager."""
    
    def __init__(self):
        self.pool: Optional[asyncpg.Pool] = None
    
    async def connect(self):
        """Create database connection pool."""
        self.pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=2,
            max_size=10
        )
    
    async def disconnect(self):
        """Close database connection pool."""
        if self.pool:
            await self.pool.close()
    
    async def get_tenant_by_api_key(self, api_key_hash: str) -> Optional[Dict[str, Any]]:
        """Get tenant by API key hash."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, name, is_active FROM tenants WHERE api_key_hash = $1",
                api_key_hash
            )
            return dict(row) if row else None
    
    async def create_document(
        self,
        tenant_id: str,
        name: str,
        content: str,
        content_type: str = "text/markdown"
    ) -> str:
        """Create a new document."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO documents (tenant_id, name, content, content_type)
                VALUES ($1, $2, $3, $4)
                RETURNING id
                """,
                tenant_id, name, content, content_type
            )
            return str(row['id'])
    
    async def get_document(self, document_id: str, tenant_id: str) -> Optional[Dict[str, Any]]:
        """Get document by ID with tenant validation."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, tenant_id, name, content, content_type, uploaded_at
                FROM documents
                WHERE id = $1 AND tenant_id = $2
                """,
                document_id, tenant_id
            )
            return dict(row) if row else None
    
    async def list_documents(self, tenant_id: str) -> List[Dict[str, Any]]:
        """List all documents for a tenant."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, content_type, uploaded_at
                FROM documents
                WHERE tenant_id = $1
                ORDER BY uploaded_at DESC
                """,
                tenant_id
            )
            return [dict(row) for row in rows]
    
    async def create_query_log(
        self,
        tenant_id: str,
        question: str,
        answer: Optional[str],
        sources: List[Dict[str, Any]],
        confidence: Optional[float],
        insufficient_context: bool,
        retrieved_chunks_count: int,
        llm_tokens_used: int,
        processing_time_ms: int
    ) -> str:
        """Log a query execution."""
        import json
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO queries (
                    tenant_id, question, answer, sources, confidence,
                    insufficient_context, retrieved_chunks_count,
                    llm_tokens_used, processing_time_ms
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                RETURNING id
                """,
                tenant_id, question, answer, json.dumps(sources), confidence,
                insufficient_context, retrieved_chunks_count, llm_tokens_used, processing_time_ms
            )
            return str(row['id'])
    
    async def create_audit_log(
        self,
        tenant_id: str,
        action: str,
        resource_type: str,
        resource_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Create an audit log entry."""
        import json
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_logs (tenant_id, action, resource_type, resource_id, metadata)
                VALUES ($1, $2, $3, $4, $5)
                """,
                tenant_id, action, resource_type, resource_id, json.dumps(metadata or {})
            )


# Global database instance
db = Database()