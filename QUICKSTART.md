# Quick Start Guide

Get the AI Knowledge Assistant running in 5 minutes.

## Prerequisites

- Docker and Docker Compose installed
- OpenAI API key

## Steps

### 1. Set up environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
nano .env
# Set: OPENAI_API_KEY=sk-your-key-here
```

### 2. Start the system

```bash
cd src/infra
docker compose up --build
```

Wait for all services to start (about 30-60 seconds). You should see:
```
knowledge-backend   | INFO:     Application startup complete.
```

### 3. Test the system

Open a new terminal and run:

```bash
cd ai-knowledge-assistant
./test_api.sh
```

This will:
- Upload sample documents (remote work policy, vacation policy)
- Ask questions and get AI-generated answers
- Test caching and tenant isolation

### 4. Try your own queries

```bash
# Upload your own document
curl -X POST http://localhost:8000/api/v1/documents \
  -H "X-API-Key: acme_test_key_hash" \
  -F "file=@your_document.md"

# Ask a question
curl -X POST http://localhost:8000/api/v1/query \
  -H "X-API-Key: acme_test_key_hash" \
  -H "Content-Type: application/json" \
  -d '{"question": "Your question here"}'
```

## API Endpoints

- `GET /api/v1/health` - Health check
- `POST /api/v1/documents` - Upload document
- `GET /api/v1/documents` - List documents
- `POST /api/v1/query` - Ask question

## Test Tenants

Two test tenants are pre-configured:

1. **Acme Corporation**
   - API Key: `acme_test_key_hash`
   
2. **TechStart Inc**
   - API Key: `techstart_test_key_hash`

## Troubleshooting

**Services not starting?**
```bash
# Check logs
docker compose logs

# Restart
docker compose down
docker compose up --build
```

**OpenAI API errors?**
- Verify your API key in `.env`
- Check you have credits in your OpenAI account

**Port already in use?**
- Change ports in `docker-compose.yml`

## Next Steps

- Read [README.md](README.md) for full documentation
- Review [AI_PROMPTS.md](AI_PROMPTS.md) for prompt engineering details
- Explore design documents in `docs/` directory

## Stopping the System

```bash
cd src/infra
docker compose down

# To also remove data volumes:
docker compose down -v
```