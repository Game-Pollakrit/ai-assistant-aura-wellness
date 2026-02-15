# AI Knowledge Assistant

An internal knowledge assistant system using RAG (Retrieval-Augmented Generation) to answer employee questions based on internal documents. Built for multi-tenant B2B SaaS environments with strict data isolation, cost control, and explainable AI outputs.

## Overview

This system allows employees to ask questions about internal policies, procedures, and documentation in natural language. The AI assistant retrieves relevant information from uploaded documents and generates accurate, cited answers using Large Language Models.

### Key Features

- **Multi-tenant isolation**: Complete data separation between tenants using separate vector collections
- **RAG pipeline**: Semantic search + LLM generation with source citations
- **Cost control**: Response caching, rate limiting, and token usage tracking
- **Explainable AI**: All answers include source citations and confidence scores
- **Production-ready**: Docker Compose deployment with PostgreSQL, Redis, and Qdrant

## Architecture

The system consists of four main components:

1. **API Layer (FastAPI)**: REST API with authentication and request validation
2. **Service Layer (Python)**: Document ingestion, query processing, and answer generation
3. **Data Layer**: PostgreSQL for structured data, Qdrant for vector embeddings, Redis for caching
4. **LLM Integration**: OpenAI API for embeddings and text generation

See [docs/A2_SYSTEM_ARCHITECTURE.md](docs/A2_SYSTEM_ARCHITECTURE.md) for detailed architecture diagrams.

## Technology Stack

- **Backend**: Python 3.11, FastAPI
- **Database**: PostgreSQL 15 (system of record)
- **Vector Database**: Qdrant (semantic search)
- **Cache**: Redis (response caching, rate limiting)
- **LLM**: OpenAI API (text-embedding-3-small, gpt-4.1-mini)
- **Infrastructure**: Docker Compose

## Design Documents

Comprehensive design documentation is available in the `docs/` directory:

- **[A1_PROBLEM_FRAMING.md](docs/A1_PROBLEM_FRAMING.md)**: User personas, decisions, and why AI is needed
- **[A2_SYSTEM_ARCHITECTURE.md](docs/A2_SYSTEM_ARCHITECTURE.md)**: High-level architecture and component design
- **[A3_DATA_MODEL.md](docs/A3_DATA_MODEL.md)**: Database schemas and tenant isolation enforcement
- **[A4_PROMPT_DESIGN.md](docs/A4_PROMPT_DESIGN.md)**: LLM prompts with structured JSON output
- **[B1_RAG_DESIGN.md](docs/B1_RAG_DESIGN.md)**: Document chunking, embeddings, and retrieval strategy
- **[C1_COST_CONTROL.md](docs/C1_COST_CONTROL.md)**: Token limits, caching, and cost optimization
- **[D1_TENANT_ISOLATION.md](docs/D1_TENANT_ISOLATION.md)**: Multi-layer isolation strategy
- **[E_EXECUTION_REALITY.md](docs/E_EXECUTION_REALITY.md)**: 2-week MVP scope and risk analysis

## Runbook

### Prerequisites

- **Docker** and **Docker Compose** installed
- **OpenAI API key** (get from https://platform.openai.com/api-keys)
- At least 4GB RAM available for Docker

### One-Command Startup

1. **Clone the repository**:
```bash
git clone <repository-url>
cd ai-knowledge-assistant
```

2. **Set up environment variables**:
```bash
cp .env.example .env
# Edit .env and add your OpenAI API key
nano .env  # or use your preferred editor
```

3. **Start all services**:
```bash
cd src/infra
docker compose up --build
```

This will:
- Build the backend Docker image
- Start PostgreSQL, Redis, and Qdrant containers
- Initialize the database schema with sample tenants
- Start the FastAPI backend on port 8000

### Environment Variables

The system requires the following environment variable:

- `OPENAI_API_KEY`: Your OpenAI API key (required)

Optional variables (defaults work with Docker Compose):
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `QDRANT_URL`: Qdrant API endpoint

See `.env.example` for all available configuration options.

### Health Checks

**Check if all services are healthy**:
```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "services": {
    "api": "healthy",
    "database": "healthy",
    "redis": "healthy",
    "qdrant": "healthy"
  }
}
```

**Individual service checks**:
```bash
# PostgreSQL
docker exec knowledge-postgres pg_isready -U knowledge_user

# Redis
docker exec knowledge-redis redis-cli ping

# Qdrant
curl http://localhost:6333/health
```

### Example API Calls

The system includes two sample tenants for testing:

- **Tenant 1**: Acme Corporation (API Key: `acme_test_key_hash`)
- **Tenant 2**: TechStart Inc (API Key: `techstart_test_key_hash`)

#### 1. Upload a Document

Create a sample document:
```bash
cat > sample_policy.md << 'EOF'
# Remote Work Policy

Employees may work remotely up to 3 days per week with manager approval.

## International Remote Work

International remote work requires HR approval and must comply with local tax laws. Employees must submit a request at least 30 days in advance.

## Equipment

The company provides laptops and monitors for remote work. Employees are responsible for maintaining a secure home office environment.
EOF
```

Upload the document:
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "X-API-Key: acme_test_key_hash" \
  -F "file=@sample_policy.md"
```

Expected response:
```json
{
  "document_id": "uuid-here",
  "name": "sample_policy.md",
  "chunks_count": 3,
  "message": "Document uploaded successfully with 3 chunks"
}
```

#### 2. Query the Knowledge Base

Ask a question:
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: acme_test_key_hash" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Can I work from another country?"
  }'
```

Expected response:
```json
{
  "answer": "Yes, you can work from another country, but it requires HR approval and must comply with local tax laws. You need to submit a request at least 30 days in advance.",
  "sources": [
    {
      "document_name": "sample_policy.md",
      "relevant_excerpt": "International remote work requires HR approval and must comply with local tax laws."
    }
  ],
  "confidence": 0.89,
  "insufficient_context": false,
  "processing_time_ms": 1234,
  "cached": false
}
```

#### 3. List Documents

```bash
curl http://localhost:8000/api/v1/documents \
  -H "X-API-Key: acme_test_key_hash"
```

#### 4. Test Tenant Isolation

Upload a document to Tenant 1:
```bash
curl -X POST http://localhost:8000/api/v1/documents \
  -H "X-API-Key: acme_test_key_hash" \
  -F "file=@sample_policy.md"
```

Try to query from Tenant 2 (should return insufficient_context):
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: techstart_test_key_hash" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the remote work policy?"
  }'
```

Expected: `insufficient_context: true` (no data leakage)

#### 5. Test Caching

Ask the same question twice:
```bash
# First call (not cached)
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: acme_test_key_hash" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the remote work policy?"}'

# Second call (cached, much faster)
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: acme_test_key_hash" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the remote work policy?"}'
```

The second response will have `"cached": true` and much lower `processing_time_ms`.

### Stopping the System

```bash
cd src/infra
docker compose down
```

To also remove volumes (clears all data):
```bash
docker compose down -v
```

## Approach

### Core Design Decisions

**Multi-tenant isolation**: Each tenant has a separate Qdrant collection for complete data isolation. All database queries include tenant_id filtering with foreign key constraints. This defense-in-depth approach prevents cross-tenant data leakage.

**RAG pipeline**: Documents are chunked into 500-token segments with 50-token overlap to preserve context. Embeddings are generated using OpenAI's text-embedding-3-small model. Queries use semantic similarity search (cosine distance) to retrieve the top 5 most relevant chunks, which are then passed to the LLM for answer generation.

**Structured output**: The LLM is prompted to return JSON with explicit fields for answer, sources, confidence, and insufficient_context flag. This ensures parseable, consistent responses and enables the system to refuse answering when information is missing.

**Cost control**: Responses are cached in Redis for 1 hour based on question + retrieved chunks. Rate limiting prevents abuse (10 queries/minute per tenant). Token usage is tracked for all LLM calls.

### Assumptions

- Documents are provided in plain text or markdown format (no PDF/DOCX parsing in MVP)
- Tenants use API key authentication (no OAuth or SSO in MVP)
- English language documents and queries (no multi-language support)
- Single-region deployment (no geo-distribution)
- Synchronous processing (no background job queues)

### Trade-offs

**Separate collections vs. shared collection**: Chose separate Qdrant collections per tenant for maximum isolation, despite higher memory overhead. In a B2B SaaS context, data leakage is unacceptable, so we prioritize security over efficiency.

**Simple caching vs. semantic similarity cache**: Implemented exact-match caching only. Semantic similarity caching (finding similar questions) would improve hit rate but adds complexity and potential for incorrect cache hits.

**Synchronous processing**: Document uploads and queries are processed synchronously. This simplifies the architecture but limits scalability. For production, would use background workers for document processing.

**No re-ranking**: Using single-stage vector search without re-ranking. Re-ranking with cross-encoders would improve precision but adds latency and cost. Can be added later based on quality metrics.

**API key auth only**: Using simple API key authentication. Production would need OAuth2, JWT tokens, and user-level permissions within tenants.

## What Would Be Improved with More Time

### High Priority

**Hybrid search**: Combine vector search with keyword search (PostgreSQL full-text search) for better recall on exact terms like policy numbers or product names.

**Re-ranking**: Add cross-encoder model to re-rank retrieved chunks for better precision. Would reduce irrelevant context in prompts.

**Document versioning**: Track document versions and allow querying specific versions. Currently, updating a document doesn't preserve history.

**User management**: Add user accounts within tenants with role-based access control. Currently, only tenant-level authentication.

**Monitoring and observability**: Add Prometheus metrics, Grafana dashboards, and structured logging. Track query quality, cache hit rates, and cost per tenant.

### Medium Priority

**Batch document processing**: Process document uploads in background workers to avoid blocking API requests.

**Advanced caching**: Implement semantic similarity cache to match similar questions. Add chunk-level caching to reduce vector search load.

**Query expansion**: Generate multiple query variations (synonyms, different phrasings) to improve retrieval recall.

**Feedback mechanism**: Allow users to rate answers and flag incorrect responses. Use feedback to improve prompts and retrieval.

**Cost analytics dashboard**: Show per-tenant cost breakdown, token usage trends, and cost optimization recommendations.

### Lower Priority

**Multi-language support**: Detect query language and use appropriate embedding models. Support non-English documents.

**Document format parsing**: Add support for PDF, DOCX, and other formats. Extract text with proper formatting preservation.

**Webhook notifications**: Notify external systems when documents are processed or queries are answered.

**Horizontal scaling**: Add load balancing, database read replicas, and distributed caching for high-traffic scenarios.

## Known Limitations

- **No PDF/DOCX support**: Only plain text and markdown documents are supported
- **English only**: System is optimized for English language; other languages may have lower quality
- **Synchronous processing**: Large document uploads may timeout; need async processing for production
- **Simple chunking**: Fixed-size chunking may split semantic units; semantic chunking would be better
- **No user-level permissions**: All users within a tenant have equal access to all documents
- **Limited error recovery**: External API failures (OpenAI, Qdrant) may cause request failures; need circuit breakers
- **No document updates**: Updating a document requires deletion and re-upload; no incremental updates

## Scaling Considerations

### Vertical Scaling (Single Instance)

Current architecture can handle:
- ~100 tenants with moderate usage
- ~10,000 documents total
- ~1,000 queries per hour

Bottlenecks:
- PostgreSQL connection pool (increase pool size)
- Qdrant memory (increase RAM or use disk-backed storage)
- Redis memory (increase RAM or use Redis Cluster)

### Horizontal Scaling (Multiple Instances)

For higher load:
- **API layer**: Stateless, can run multiple FastAPI instances behind load balancer
- **PostgreSQL**: Use read replicas for query-heavy workloads
- **Redis**: Use Redis Cluster for distributed caching
- **Qdrant**: Use Qdrant cluster mode for distributed vector search

### Cost Scaling

At 1,000 queries/day per tenant:
- Embedding cost: ~$0.10/day (assuming 500 tokens per query)
- Completion cost: ~$1.50/day (assuming 2,500 tokens input + 500 tokens output)
- Total: ~$1.60/day per tenant = ~$50/month per tenant

Caching can reduce costs by 30-40% for tenants with repeated questions.

## Development

### Local Development (without Docker)

Install dependencies:
```bash
cd src/backend
pip install -r requirements.txt
```

Start services manually:
```bash
# PostgreSQL
docker run -d -p 5432:5432 -e POSTGRES_PASSWORD=knowledge_pass postgres:15

# Redis
docker run -d -p 6379:6379 redis:7

# Qdrant
docker run -d -p 6333:6333 qdrant/qdrant
```

Run the backend:
```bash
export OPENAI_API_KEY=your_key_here
export DATABASE_URL=postgresql://postgres:knowledge_pass@localhost:5432/postgres
uvicorn main:app --reload
```

### Running Tests

```bash
# TODO: Add pytest tests
cd src/backend
pytest
```

## License

This project is for demonstration purposes as part of an AI Engineer assessment.
