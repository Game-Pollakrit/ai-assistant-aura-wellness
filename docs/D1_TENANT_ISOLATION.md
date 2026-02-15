# D1. Tenant Isolation Strategy

## Preventing Cross-Tenant Leakage in Prompts

### Isolation Layers

**Layer 1: Collection-Level Isolation**
Each tenant's documents are stored in a separate Qdrant collection:
```python
collection_name = f"tenant_{tenant_id}_documents"
```

This provides **physical isolation** at the storage level. Even if application logic fails, there is no way to accidentally retrieve another tenant's documents because the collections are completely separate.

**Layer 2: Metadata Filtering**
As a defense-in-depth measure, all vector searches include tenant_id in the filter:
```python
search_filter = Filter(
    must=[
        FieldCondition(key="tenant_id", match=MatchValue(value=tenant_id))
    ]
)
```

This protects against:
- Collection naming bugs
- Misconfigured collection mappings
- Future refactoring errors

**Layer 3: Application-Level Validation**
Every API request extracts and validates tenant_id from authentication before any operation:
```python
async def get_tenant_context(api_key: str = Header(...)) -> TenantContext:
    tenant = await auth_service.validate_api_key(api_key)
    if not tenant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    if not tenant.is_active:
        raise HTTPException(status_code=403, detail="Tenant account inactive")
    
    return TenantContext(
        tenant_id=tenant.id,
        tenant_name=tenant.name,
        tier=tenant.tier
    )
```

### Prompt Construction Safety

**Context Assembly**
When building the prompt, only chunks from the tenant-specific search are included:
```python
async def build_prompt(
    question: str,
    tenant_id: str
) -> str:
    # Search only returns tenant-scoped chunks
    chunks = await vector_search(
        question=question,
        tenant_id=tenant_id,  # Enforced here
        collection=f"tenant_{tenant_id}_documents"
    )
    
    # Build context from retrieved chunks
    context = "\n\n".join([
        f"--- Document: {chunk.document_name} ---\n{chunk.text}\n---"
        for chunk in chunks
    ])
    
    # System prompt includes tenant name for context
    system_prompt = f"""You are an internal knowledge assistant for {tenant_name}.
    Answer questions based ONLY on the provided documents.
    Never use information from other sources or companies."""
    
    user_prompt = f"""CONTEXT:\n{context}\n\nQUESTION: {question}"""
    
    return system_prompt, user_prompt
```

**No Cross-Tenant Context Mixing**
The system ensures that:
1. Vector search is scoped to single tenant collection
2. Retrieved chunks all have matching tenant_id
3. No caching or memoization across tenant boundaries
4. Each request is completely isolated

### Validation Checks
```python
async def validate_chunks_tenant_isolation(
    chunks: List[Chunk],
    expected_tenant_id: str
):
    """Verify all chunks belong to expected tenant"""
    for chunk in chunks:
        if chunk.tenant_id != expected_tenant_id:
            # Critical security violation
            await security_alert.trigger(
                severity="CRITICAL",
                message=f"Tenant isolation breach detected",
                details={
                    "expected_tenant": expected_tenant_id,
                    "found_tenant": chunk.tenant_id,
                    "chunk_id": chunk.id
                }
            )
            raise SecurityException("Tenant isolation violation")
```

## Vector Search Scoping

### Collection Architecture

**Option 1: Separate Collections (IMPLEMENTED)**
```
tenant_a1b2c3_documents  (Collection 1)
tenant_d4e5f6_documents  (Collection 2)
tenant_g7h8i9_documents  (Collection 3)
```

**Advantages:**
- Complete physical isolation
- No risk of filter bypass
- Independent scaling per tenant
- Easy tenant deletion (drop collection)

**Disadvantages:**
- More collections to manage
- Slightly higher memory overhead

**Option 2: Shared Collection with Filtering (NOT USED)**
```
all_documents  (Single collection with tenant_id in payload)
```

**Advantages:**
- Simpler infrastructure
- Easier to manage at scale

**Disadvantages:**
- Relies on filter correctness
- Risk of filter bypass bugs
- Harder to audit isolation

**Decision: Use separate collections** for maximum security in a B2B SaaS environment where data leakage is unacceptable.

### Search Implementation
```python
async def search_tenant_documents(
    query_vector: List[float],
    tenant_id: str,
    top_k: int = 5,
    score_threshold: float = 0.7
) -> List[SearchResult]:
    """Search documents with strict tenant isolation"""
    
    collection_name = f"tenant_{tenant_id}_documents"
    
    # Verify collection exists
    collections = await qdrant_client.get_collections()
    if collection_name not in [c.name for c in collections.collections]:
        raise CollectionNotFoundError(f"No documents for tenant {tenant_id}")
    
    # Search with redundant tenant filter
    results = await qdrant_client.search(
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
    
    # Post-search validation
    for result in results:
        assert result.payload["tenant_id"] == tenant_id, \
            "Tenant isolation breach in search results"
    
    return results
```

### Collection Lifecycle

**Creation:**
```python
async def create_tenant_collection(tenant_id: str):
    collection_name = f"tenant_{tenant_id}_documents"
    
    await qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=1536,  # text-embedding-3-small
            distance=Distance.COSINE
        )
    )
    
    # Create index for tenant_id filtering
    await qdrant_client.create_payload_index(
        collection_name=collection_name,
        field_name="tenant_id",
        field_schema=PayloadSchemaType.KEYWORD
    )
```

**Deletion:**
```python
async def delete_tenant_data(tenant_id: str):
    """Complete tenant data deletion for GDPR compliance"""
    
    # Delete vector collection
    collection_name = f"tenant_{tenant_id}_documents"
    await qdrant_client.delete_collection(collection_name)
    
    # Delete PostgreSQL data (cascades via foreign keys)
    await db.execute(
        "DELETE FROM tenants WHERE id = $1",
        tenant_id
    )
    
    # Clear Redis cache
    pattern = f"*{tenant_id}*"
    keys = await redis.keys(pattern)
    if keys:
        await redis.delete(*keys)
    
    # Audit log
    await audit_log.log(
        action="tenant_deleted",
        tenant_id=tenant_id,
        timestamp=datetime.utcnow()
    )
```

## Audit Trail

### Logging Strategy
Every operation that touches tenant data is logged:
```python
@dataclass
class AuditLogEntry:
    tenant_id: str
    action: str  # 'query', 'document_upload', 'document_delete'
    resource_type: str  # 'document', 'query'
    resource_id: str
    user_id: Optional[str]
    ip_address: str
    timestamp: datetime
    metadata: dict
```

### Critical Events to Log
1. **Document Access**: Every document retrieval for a query
2. **Query Execution**: Question asked, chunks retrieved, answer generated
3. **Document Upload**: New documents added to tenant collection
4. **Document Deletion**: Documents removed from tenant collection
5. **Authentication**: API key usage and validation
6. **Rate Limit Violations**: Attempts to exceed quotas
7. **Security Violations**: Any tenant_id mismatch or isolation breach

### Audit Query Examples
```python
# Find all queries that accessed a specific document
SELECT * FROM audit_logs
WHERE tenant_id = 'tenant-123'
  AND action = 'query'
  AND metadata->>'document_id' = 'doc-456'
ORDER BY timestamp DESC;

# Detect suspicious cross-tenant access attempts
SELECT * FROM audit_logs
WHERE action = 'security_violation'
  AND metadata->>'violation_type' = 'tenant_mismatch'
ORDER BY timestamp DESC;

# Track tenant activity over time
SELECT 
    DATE(timestamp) as date,
    action,
    COUNT(*) as count
FROM audit_logs
WHERE tenant_id = 'tenant-123'
GROUP BY DATE(timestamp), action
ORDER BY date DESC;
```

## Testing Tenant Isolation

### Unit Tests
```python
async def test_cross_tenant_search_isolation():
    """Verify tenant A cannot search tenant B's documents"""
    
    # Create two tenants
    tenant_a = await create_tenant("Company A")
    tenant_b = await create_tenant("Company B")
    
    # Upload document to tenant A
    doc_a = await upload_document(
        tenant_id=tenant_a.id,
        content="Company A confidential data"
    )
    
    # Try to search from tenant B
    results = await search_documents(
        question="confidential data",
        tenant_id=tenant_b.id
    )
    
    # Should return no results
    assert len(results) == 0, "Cross-tenant data leakage detected"
```

### Integration Tests
```python
async def test_prompt_isolation():
    """Verify prompts only include tenant-scoped context"""
    
    tenant_id = "test-tenant-123"
    
    # Upload documents
    await upload_document(tenant_id, "Document 1 content")
    await upload_document(tenant_id, "Document 2 content")
    
    # Execute query
    response = await query_service.execute(
        question="What is in the documents?",
        tenant_id=tenant_id
    )
    
    # Verify all sources belong to tenant
    for source in response.sources:
        doc = await db.get_document(source.document_id)
        assert doc.tenant_id == tenant_id, "Source from wrong tenant"
```

### Penetration Testing Scenarios
1. **API Key Swapping**: Try to use tenant A's API key with tenant B's document IDs
2. **Collection Name Injection**: Attempt to inject different collection names in queries
3. **Filter Bypass**: Try to search without tenant_id filter
4. **Cache Poisoning**: Attempt to cache responses with wrong tenant_id


