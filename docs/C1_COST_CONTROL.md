# C1. Cost Control Strategy

## Token Usage Limits

### Per-Request Limits
```python
MAX_CONTEXT_TOKENS = 2500  # ~5 chunks × 500 tokens
MAX_COMPLETION_TOKENS = 1000  # Sufficient for detailed answers
MAX_TOTAL_TOKENS = 4000  # Context + completion + system prompt
```

### Per-Tenant Rate Limits
```python
RATE_LIMITS = {
    "queries_per_minute": 10,
    "queries_per_hour": 100,
    "queries_per_day": 1000,
    "embeddings_per_hour": 500,  # Document uploads
}
```

### Implementation
```python
async def check_rate_limit(tenant_id: str, operation: str) -> bool:
    key = f"ratelimit:{tenant_id}:{operation}:{current_minute}"
    count = await redis.incr(key)
    
    if count == 1:
        await redis.expire(key, 60)  # 1-minute window
    
    limit = RATE_LIMITS.get(f"{operation}_per_minute", 10)
    
    if count > limit:
        raise RateLimitExceeded(f"Rate limit exceeded: {limit} {operation}/minute")
    
    return True
```

## Response Caching Strategy

### Cache Key Design
```python
def generate_cache_key(tenant_id: str, question: str, chunk_ids: List[str]) -> str:
    # Include chunk_ids to invalidate cache when documents change
    content = f"{tenant_id}:{question}:{':'.join(sorted(chunk_ids))}"
    return f"cache:llm:{hashlib.sha256(content.encode()).hexdigest()}"
```

### Cache Levels

**Level 1: Exact Question Match (1 hour TTL)**
- Cache complete LLM responses for identical questions
- Invalidate when source documents are updated or deleted
- Hit rate: ~30-40% for common questions (e.g., "What is the vacation policy?")

**Level 2: Semantic Similarity Cache (Future)**
- Cache responses for semantically similar questions
- Use embedding similarity to find cached answers (threshold > 0.95)
- Example: "What's the remote work policy?" ≈ "Can I work from home?"

**Level 3: Chunk Retrieval Cache (15 minutes TTL)**
- Cache vector search results for common queries
- Reduces Qdrant load for repeated searches
- Key: `cache:retrieval:{hash(tenant_id + question_embedding)}`

### Cache Invalidation
```python
async def invalidate_document_cache(tenant_id: str, document_id: str):
    # Find all cached responses that used this document
    pattern = f"cache:llm:*{document_id}*"
    keys = await redis.keys(pattern)
    
    if keys:
        await redis.delete(*keys)
    
    # Log invalidation for monitoring
    await audit_log.log(
        tenant_id=tenant_id,
        action="cache_invalidate",
        resource_id=document_id
    )
```

## When to Cache AI Responses

### Cache These Scenarios
1. **FAQ-style questions**: High-frequency, low-variability questions
2. **Policy lookups**: Stable information that changes infrequently
3. **Identical questions**: Exact string match with same retrieved context

### Do NOT Cache These Scenarios
1. **Time-sensitive queries**: "What's the deadline for Q4 reports?"
2. **User-specific questions**: Questions containing personal identifiers
3. **Low-confidence answers**: Responses with confidence < 0.7
4. **Insufficient context responses**: No point caching failures

### Implementation
```python
async def should_cache_response(
    response: QueryResponse,
    question: str
) -> bool:
    # Don't cache low-quality responses
    if response.confidence < 0.7:
        return False
    
    if response.insufficient_context:
        return False
    
    # Don't cache time-sensitive queries
    time_keywords = ["today", "now", "current", "latest", "deadline"]
    if any(kw in question.lower() for kw in time_keywords):
        return False
    
    # Don't cache user-specific queries
    personal_keywords = ["my", "i ", "me ", "mine"]
    if any(kw in question.lower() for kw in personal_keywords):
        return False
    
    return True
```

## When AI Should NOT Be Used

### Rule-Based Alternatives
AI is overkill for these scenarios:

**1. Exact Keyword Lookups**
- Question: "Show me document X"
- Solution: Direct database query by document name
- Cost: $0 (no LLM call)

**2. Structured Data Queries**
- Question: "How many documents do we have?"
- Solution: SQL COUNT query
- Cost: $0 (no LLM call)

**3. Navigation/Listing**
- Question: "List all HR policies"
- Solution: Database query with category filter
- Cost: $0 (no LLM call)

**4. Simple Keyword Search**
- Question: "Documents containing 'vacation'"
- Solution: PostgreSQL full-text search or Elasticsearch
- Cost: $0 (no LLM call)

### Pre-Processing Layer
```python
async def route_query(question: str, tenant_id: str) -> QueryResponse:
    # Detect intent
    intent = await intent_classifier.classify(question)
    
    if intent == "document_lookup":
        # Direct database query
        return await db.find_document_by_name(question, tenant_id)
    
    elif intent == "list_documents":
        # Return document list
        return await db.list_documents(tenant_id)
    
    elif intent == "keyword_search":
        # Use PostgreSQL full-text search
        return await db.fulltext_search(question, tenant_id)
    
    else:
        # Use AI for complex semantic queries
        return await ai_query_service.execute(question, tenant_id)
```

### Cost Comparison

| Query Type | Traditional | AI-Powered | Cost Savings |
|------------|-------------|------------|--------------|
| Document lookup | $0.0001 | $0.002 | 20x cheaper |
| Keyword search | $0.0005 | $0.002 | 4x cheaper |
| Semantic Q&A | Not possible | $0.002 | AI required |
| Multi-doc reasoning | Not possible | $0.003 | AI required |

## Cost Monitoring

### Metrics to Track
```python
# Per-tenant cost tracking
cost_metrics = {
    "embedding_tokens": 0,      # Input tokens for embeddings
    "completion_tokens": 0,     # Output tokens from LLM
    "prompt_tokens": 0,         # Input tokens for completions
    "total_cost_usd": 0.0,
    "queries_count": 0,
    "cache_hit_rate": 0.0,
}
```

### Cost Calculation
```python
# OpenAI pricing (as of 2024)
EMBEDDING_COST_PER_1K = 0.00002  # text-embedding-3-small
COMPLETION_INPUT_COST_PER_1K = 0.00015  # gpt-4.1-mini input
COMPLETION_OUTPUT_COST_PER_1K = 0.0006  # gpt-4.1-mini output

async def calculate_query_cost(
    prompt_tokens: int,
    completion_tokens: int,
    embedding_tokens: int
) -> float:
    embedding_cost = (embedding_tokens / 1000) * EMBEDDING_COST_PER_1K
    input_cost = (prompt_tokens / 1000) * COMPLETION_INPUT_COST_PER_1K
    output_cost = (completion_tokens / 1000) * COMPLETION_OUTPUT_COST_PER_1K
    
    return embedding_cost + input_cost + output_cost
```

### Alerting Thresholds
```python
COST_ALERTS = {
    "daily_cost_per_tenant": 10.0,  # Alert if tenant exceeds $10/day
    "hourly_spike": 5.0,            # Alert if $5 spent in 1 hour
    "cache_hit_rate_low": 0.2,      # Alert if cache hit rate < 20%
}
```

## Optimization Strategies

### 1. Prompt Compression
- Remove unnecessary whitespace and formatting from context chunks
- Use abbreviated field names in JSON output
- Estimated savings: 10-15% token reduction

### 2. Model Selection
- Use `gpt-4.1-mini` instead of `gpt-4o` for most queries (10x cheaper)
- Reserve `gpt-4o` for complex multi-document reasoning
- Estimated savings: 90% cost reduction for standard queries

### 3. Batch Processing
- Batch document embedding during off-peak hours
- Process multiple chunks in parallel
- Estimated savings: 20% faster processing, same cost

### 4. Smart Chunking
- Avoid embedding duplicate or boilerplate content (headers, footers)
- Skip embedding non-informative sections
- Estimated savings: 15-20% fewer embeddings

### 5. Response Streaming
- Stream LLM responses to improve perceived latency
- Stop generation early if sufficient answer is generated
- Estimated savings: 10-20% fewer completion tokens