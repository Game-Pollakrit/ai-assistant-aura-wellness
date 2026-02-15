# Section E — Execution Reality Check

## What would you ship in 2 weeks?

### Week 1: Core Infrastructure + MVP
**Days 1-3: Foundation**
- Docker Compose setup with PostgreSQL, Redis, Qdrant
- Database schema with tenant isolation
- FastAPI skeleton with authentication middleware
- Basic document upload endpoint (no chunking yet, store full documents)

**Days 4-5: Basic RAG**
- Document chunking and embedding pipeline
- Qdrant collection creation and vector storage
- Simple vector search endpoint (no LLM yet, just return chunks)

**Week 2: AI Integration + Polish**
**Days 6-8: LLM Integration**
- OpenAI API integration for embeddings and completions
- Prompt engineering with structured JSON output
- Query endpoint with RAG pipeline (retrieve + generate)
- Basic caching in Redis for identical questions

**Days 9-10: Testing + Documentation**
- End-to-end testing with sample documents
- README with runbook (docker compose up, example curl commands)
- AI_PROMPTS.md with actual prompts used
- Basic error handling and logging

### What Would Be Shipped
✅ **Working backend API** with 3 core endpoints:
- `POST /api/v1/documents` - Upload markdown documents
- `POST /api/v1/query` - Ask questions and get AI answers with sources
- `GET /api/v1/health` - Health check endpoint

✅ **Multi-tenant isolation** via separate Qdrant collections + tenant_id filtering

✅ **Basic RAG pipeline**: Document chunking → embeddings → vector search → LLM generation

✅ **Source citation**: Answers include document names and relevant excerpts

✅ **Docker Compose deployment**: One-command startup with all dependencies

✅ **Minimal viable caching**: Cache LLM responses for identical questions (1-hour TTL)

✅ **Basic rate limiting**: 10 queries/minute per tenant via Redis

### Quality Bar
- **Architecture**: Correct and extensible
- **Code**: Functional but not production-polished (some TODOs acceptable)
- **Testing**: Manual testing with curl, basic happy path coverage
- **Documentation**: Clear enough for another engineer to run and understand

## What would you explicitly NOT build yet?

### Features to Defer

❌ **Advanced RAG techniques**
- Hybrid search (vector + keyword)
- Re-ranking with cross-encoder models
- Query expansion or multi-query strategies
- **Why defer**: Core semantic search is sufficient for MVP; these add complexity without proving value first

❌ **Sophisticated caching**
- Semantic similarity cache (finding similar questions)
- Chunk-level caching
- Predictive pre-caching
- **Why defer**: Simple exact-match caching captures most gains; advanced caching requires analytics to justify

❌ **User management UI**
- Admin dashboard for document management
- Query history visualization
- Cost analytics dashboard
- **Why defer**: Assignment specifies "no frontend required"; focus on backend correctness

❌ **Advanced cost optimization**
- Prompt compression algorithms
- Dynamic model selection (gpt-4.1-mini vs gpt-4o)
- Batch embedding processing
- **Why defer**: Optimize after measuring actual usage patterns; premature optimization wastes time

❌ **Comprehensive monitoring**
- Prometheus metrics
- Grafana dashboards
- Alerting system
- **Why defer**: Basic logging is sufficient for 2-week MVP; add observability based on production needs

❌ **Production hardening**
- Horizontal scaling setup
- Database connection pooling tuning
- Circuit breakers for external APIs
- Comprehensive error recovery
- **Why defer**: These are important for production but overkill for demonstrating AI engineering skills

❌ **Advanced security**
- Row-level security in PostgreSQL
- API key rotation mechanism
- Encryption at rest
- **Why defer**: Basic tenant isolation is sufficient for demo; add security layers for production

### Pseudocode Acceptable For
- Document format parsing (PDF, DOCX) - assume markdown input only
- User authentication beyond API key - assume simple API key auth
- Webhook notifications - not needed for core flow
- Batch document processing - handle one document at a time

## What risks worry you the most?

### Technical Risks

**1. Hallucination Despite RAG (HIGH)**
- **Risk**: LLM generates plausible but incorrect answers even with correct context
- **Impact**: Users trust wrong information, leading to compliance issues or bad decisions
- **Mitigation**:
  - Require source citations in structured output
  - Add confidence scores and threshold filtering
  - Log all Q&A pairs for human review
  - Implement feedback mechanism to flag incorrect answers

**2. Vector Search Quality (MEDIUM)**
- **Risk**: Semantic search fails to retrieve relevant chunks for certain query types
- **Impact**: "Insufficient context" responses even when information exists
- **Mitigation**:
  - Test with diverse question phrasings
  - Monitor retrieval precision/recall metrics
  - Implement fallback to keyword search
  - Allow users to specify document scope

**3. Cost Runaway (MEDIUM)**
- **Risk**: Malicious or accidental API abuse leads to unexpected LLM costs
- **Impact**: Budget blown, service becomes unsustainable
- **Mitigation**:
  - Strict rate limiting per tenant
  - Cost monitoring and alerting
  - Cache aggressively
  - Set per-tenant monthly quotas

**4. Tenant Isolation Bug (HIGH)**
- **Risk**: Code bug or misconfiguration leaks data across tenants
- **Impact**: Catastrophic breach of trust, legal liability, contract violations
- **Mitigation**:
  - Multi-layer isolation (collection + filter + validation)
  - Comprehensive audit logging
  - Automated tests for cross-tenant access
  - Security code review before deployment

### Operational Risks

**5. Document Quality Variability (MEDIUM)**
- **Risk**: Poorly formatted or outdated documents reduce answer quality
- **Impact**: Users lose trust in the system
- **Mitigation**:
  - Document quality scoring during upload
  - Warn users about low-quality documents
  - Implement document versioning
  - Add "last updated" metadata to sources

**6. Context Window Limitations (LOW)**
- **Risk**: Long documents or complex questions exceed LLM context window
- **Impact**: Incomplete answers or errors
- **Mitigation**:
  - Chunk documents appropriately (500 tokens)
  - Limit number of chunks in context (5 chunks)
  - Use models with larger context windows if needed

**7. Dependency Failures (MEDIUM)**
- **Risk**: OpenAI API downtime, Qdrant crashes, Redis unavailable
- **Impact**: Service outage, degraded user experience
- **Mitigation**:
  - Graceful degradation (serve cached responses if LLM unavailable)
  - Health checks for all dependencies
  - Retry logic with exponential backoff
  - Clear error messages to users

### Product Risks

**8. User Expectation Mismatch (HIGH)**
- **Risk**: Users expect ChatGPT-level reasoning but get narrow document-based answers
- **Impact**: Disappointment, low adoption
- **Mitigation**:
  - Clear documentation of system capabilities and limitations
  - Show confidence scores and "insufficient context" messages
  - Provide example questions that work well
  - Gather user feedback early

**9. Insufficient Training Data (MEDIUM)**
- **Risk**: Tenants upload too few documents for useful answers
- **Impact**: System appears broken or useless
- **Mitigation**:
  - Recommend minimum document corpus size (e.g., 20+ documents)
  - Provide sample documents for testing
  - Show coverage metrics (% of questions answerable)

**10. Prompt Injection Attacks (LOW)**
- **Risk**: Users craft questions to manipulate LLM behavior or extract system prompts
- **Impact**: Unexpected behavior, potential security issues
- **Mitigation**:
  - Input validation and sanitization
  - System prompt hardening
  - Monitor for suspicious patterns
  - Rate limiting prevents large-scale attacks

## Risk Prioritization

| Risk | Severity | Likelihood | Priority | Mitigation Effort |
|------|----------|------------|----------|-------------------|
| Tenant isolation bug | Critical | Low | **P0** | High (must do) |
| Hallucination | High | Medium | **P0** | Medium (must do) |
| User expectation mismatch | High | High | **P1** | Low (documentation) |
| Cost runaway | Medium | Medium | **P1** | Medium (rate limits + monitoring) |
| Vector search quality | Medium | Medium | **P2** | High (ongoing tuning) |
| Document quality | Medium | High | **P2** | Medium (validation + feedback) |
| Dependency failures | Medium | Low | **P2** | Medium (health checks + retries) |
| Context window limits | Low | Low | **P3** | Low (chunking strategy) |
| Prompt injection | Low | Low | **P3** | Low (input validation) |

## Success Criteria for 2-Week MVP

✅ **Functional**: Another engineer can clone, run `docker compose up --build`, and successfully:
- Upload a markdown document
- Ask a question and get an answer with sources
- Verify tenant isolation (upload to tenant A, query from tenant B returns nothing)

✅ **Correct Architecture**: Design documents demonstrate understanding of:
- Multi-tenant isolation strategies
- RAG pipeline design
- Cost control mechanisms
- Production considerations

✅ **Explainable**: AI_PROMPTS.md shows:
- Actual prompts used
- Reasoning behind prompt structure
- Examples of accepted/rejected outputs

✅ **Production-Ready Thinking**: README explains:
- What would be improved with more time
- Known limitations and trade-offs
- Scaling considerations
