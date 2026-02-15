# A3. Data Model

## PostgreSQL Schema

### Tenants Table
```sql
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    api_key_hash VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_tenants_api_key ON tenants(api_key_hash);
```

### Documents Table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    content_type VARCHAR(50) DEFAULT 'text/markdown',
    metadata JSONB DEFAULT '{}',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

-- Enforce tenant isolation at database level
CREATE INDEX idx_documents_tenant ON documents(tenant_id);
CREATE INDEX idx_documents_tenant_name ON documents(tenant_id, name);
```

### Queries Table (AI Request/Result Log)
```sql
CREATE TABLE queries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    answer TEXT,
    sources JSONB DEFAULT '[]',
    confidence DECIMAL(3,2),
    insufficient_context BOOLEAN DEFAULT FALSE,
    retrieved_chunks_count INTEGER,
    llm_tokens_used INTEGER,
    processing_time_ms INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_queries_tenant ON queries(tenant_id);
CREATE INDEX idx_queries_tenant_created ON queries(tenant_id, created_at DESC);
```

### Audit Logs Table
```sql
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    action VARCHAR(100) NOT NULL, -- 'document_upload', 'query_execute', 'document_delete'
    resource_type VARCHAR(50) NOT NULL, -- 'document', 'query'
    resource_id UUID,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
);

CREATE INDEX idx_audit_tenant_created ON audit_logs(tenant_id, created_at DESC);
```

## Vector Database Schema (Qdrant)

### Collection Structure
```python
# Collection naming: tenant_{tenant_id}_documents
# Example: tenant_a1b2c3d4_documents

collection_config = {
    "vectors": {
        "size": 1536,  # text-embedding-3-small dimension
        "distance": "Cosine"
    }
}

# Point payload structure
payload = {
    "tenant_id": "a1b2c3d4-...",  # Redundant safety layer
    "document_id": "doc-uuid",
    "document_name": "Employee Handbook 2024.md",
    "chunk_text": "Remote work policy allows...",
    "chunk_index": 0,
    "total_chunks": 15,
    "uploaded_at": "2024-01-15T10:30:00Z"
}
```

## Redis Key Patterns

```
# LLM Response Cache
cache:llm:{sha256(tenant_id+question+chunk_ids)} -> JSON response
TTL: 3600 seconds

# Rate Limiting
ratelimit:tenant:{tenant_id}:query -> counter
TTL: 60 seconds (sliding window)

# Idempotency
idempotency:{request_id} -> response
TTL: 300 seconds
```

## Tenant Isolation Enforcement

### Database Level (PostgreSQL)
1. **Foreign Key Constraints**: All tables reference `tenants(id)` with `ON DELETE CASCADE`
2. **Row-Level Security (RLS)**: Could be enabled for additional safety:
```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON documents
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);
```
3. **Application-Level Filtering**: Every query includes `WHERE tenant_id = ?` parameter

### Vector Database Level (Qdrant)
1. **Collection Isolation**: Each tenant has a dedicated collection (`tenant_{id}_documents`)
2. **Metadata Filtering**: Even with separate collections, all searches include tenant_id filter:
```python
search_params = {
    "filter": {
        "must": [
            {"key": "tenant_id", "match": {"value": tenant_id}}
        ]
    }
}
```

### Application Level (Service Layer)
1. **Context Object**: Every request creates a `TenantContext` object extracted from authentication
2. **Dependency Injection**: FastAPI dependencies ensure tenant_id is validated before any database operation
3. **Audit Trail**: All operations logged with tenant_id in `audit_logs` table

### Example Enforcement in Code
```python
class TenantContext:
    def __init__(self, tenant_id: str, tenant_name: str):
        self.tenant_id = tenant_id
        self.tenant_name = tenant_name

async def get_tenant_context(api_key: str = Header(...)) -> TenantContext:
    # Validate API key and return tenant context
    tenant = await db.get_tenant_by_api_key(api_key)
    if not tenant:
        raise HTTPException(401, "Invalid API key")
    return TenantContext(tenant.id, tenant.name)

@app.post("/api/v1/query")
async def query(
    request: QueryRequest,
    context: TenantContext = Depends(get_tenant_context)
):
    # All operations automatically scoped to context.tenant_id
    results = await query_service.execute(
        question=request.question,
        tenant_id=context.tenant_id  # Enforced here
    )
```

## Data Flow Example

**Document Upload**:
1. API receives document + API key
2. Extract tenant_id from API key
3. Insert into `documents` table with tenant_id
4. Chunk document into 500-token segments
5. Generate embeddings for each chunk
6. Store in Qdrant collection `tenant_{tenant_id}_documents` with tenant_id in payload
7. Log action in `audit_logs`

**Query Processing**:
1. API receives question + API key
2. Extract tenant_id from API key
3. Check Redis cache: `cache:llm:{hash(tenant_id+question)}`
4. If miss: Generate question embedding
5. Search Qdrant collection `tenant_{tenant_id}_documents` with tenant_id filter
6. Retrieve top 5 chunks
7. Build prompt with context + question
8. Call LLM with structured output format
9. Store result in `queries` table with tenant_id
10. Cache response in Redis
11. Log action in `audit_logs`