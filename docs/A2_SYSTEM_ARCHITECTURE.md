# A2. System Architecture

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                          API Layer (FastAPI)                     │
│  - Authentication & Tenant Context Extraction                    │
│  - Request Validation & Rate Limiting                            │
│  - Response Formatting & Error Handling                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
┌────────────────▼────────────────────────────────────────────────┐
│                      Service Layer (Python)                      │
│                                                                   │
│  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────┐ │
│  │  Document       │  │  Query           │  │  Answer        │ │
│  │  Ingestion      │  │  Processing      │  │  Generation    │ │
│  │  Service        │  │  Service         │  │  Service       │ │
│  └─────────────────┘  └──────────────────┘  └────────────────┘ │
│                                                                   │
└───┬─────────────────────┬──────────────────────┬────────────────┘
    │                     │                      │
    │                     │                      │
┌───▼──────────┐  ┌──────▼──────────┐  ┌────────▼──────────┐
│  PostgreSQL  │  │  Qdrant         │  │  Redis            │
│              │  │  (Vector DB)    │  │                   │
│  - Tenants   │  │                 │  │  - LLM Response   │
│  - Documents │  │  - Embeddings   │  │    Cache          │
│  - Queries   │  │  - Metadata     │  │  - Rate Limit     │
│  - Audit Log │  │  - Tenant       │  │    Tracking       │
│              │  │    Filtering    │  │  - Idempotency    │
└──────────────┘  └─────────────────┘  └───────────────────┘
                           │
                  ┌────────▼────────┐
                  │  OpenAI API     │
                  │  (Embeddings +  │
                  │   Completion)   │
                  └─────────────────┘
```

## Component Descriptions

### API Layer (FastAPI)
- **Technology**: FastAPI with Pydantic for request/response validation
- **Authentication**: Tenant ID extracted from API key or JWT token
- **Endpoints**:
  - `POST /api/v1/documents/upload` - Ingest documents
  - `POST /api/v1/query` - Ask questions
  - `GET /api/v1/documents` - List documents
  - `GET /api/v1/queries/{query_id}` - Get query results

### LLM Usage
- **Embedding Model**: `text-embedding-3-small` (OpenAI) - for document and query vectorization
- **Completion Model**: `gpt-4.1-mini` - for answer generation with structured output
- **Prompt Strategy**: System prompt defines role, user prompt contains retrieved context + question

### Prompt Layer
- **System Prompt**: Defines AI as internal knowledge assistant with strict source citation requirements
- **Context Injection**: Retrieved document chunks with metadata (document name, section)
- **Output Format**: Structured JSON with `answer`, `sources[]`, and `confidence` fields
- **Refusal Logic**: Explicit instruction to return `"insufficient_context": true` when information is missing

### PostgreSQL Schema (High-Level)
```sql
-- Tenant isolation at row level
tenants (id, name, api_key_hash, created_at)

-- Source documents with tenant ownership
documents (id, tenant_id, name, content, content_type, uploaded_at)

-- Query history for audit and analytics
queries (id, tenant_id, question, answer, sources, confidence, created_at)

-- Audit log for compliance
audit_logs (id, tenant_id, action, resource_type, resource_id, timestamp)
```

### Vector DB Usage (Qdrant)
- **Collection per tenant**: `tenant_{tenant_id}_documents` for complete isolation
- **Payload**: Stores document_id, chunk_text, document_name, chunk_index, tenant_id
- **Search**: Semantic similarity search with tenant_id filter as safety layer
- **Chunking**: Documents split into 500-token chunks with 50-token overlap

### Redis Usage
- **LLM Response Cache**: Key = `hash(tenant_id + question + context_chunk_ids)`, TTL = 1 hour
- **Rate Limiting**: Key = `ratelimit:tenant:{tenant_id}:{endpoint}`, sliding window counter
- **Idempotency**: Key = `idempotency:{request_id}`, TTL = 5 minutes for duplicate request detection