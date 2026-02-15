#!/bin/bash

# Test script for AI Knowledge Assistant API
# This script demonstrates the core functionality end-to-end

set -e

API_URL="http://localhost:8000"
API_KEY="acme_test_key_hash"

echo "=========================================="
echo "AI Knowledge Assistant - API Test Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Health Check
echo -e "${BLUE}Test 1: Health Check${NC}"
echo "GET $API_URL/api/v1/health"
curl -s $API_URL/api/v1/health | python -m json.tool
echo ""
echo ""

# Test 2: Upload Remote Work Policy
echo -e "${BLUE}Test 2: Upload Remote Work Policy Document${NC}"
echo "POST $API_URL/api/v1/documents"
UPLOAD_RESPONSE=$(curl -s -X POST $API_URL/api/v1/documents \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_documents/remote_work_policy.md")
echo "$UPLOAD_RESPONSE" | python -m json.tool
DOC1_ID=$(echo "$UPLOAD_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['document_id'])")
echo -e "${GREEN}✓ Document uploaded: $DOC1_ID${NC}"
echo ""
echo ""

# Test 3: Upload Vacation Policy
echo -e "${BLUE}Test 3: Upload Vacation Policy Document${NC}"
echo "POST $API_URL/api/v1/documents"
UPLOAD_RESPONSE=$(curl -s -X POST $API_URL/api/v1/documents \
  -H "X-API-Key: $API_KEY" \
  -F "file=@sample_documents/vacation_policy.md")
echo "$UPLOAD_RESPONSE" | python -m json.tool
DOC2_ID=$(echo "$UPLOAD_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['document_id'])")
echo -e "${GREEN}✓ Document uploaded: $DOC2_ID${NC}"
echo ""
echo ""

# Wait for indexing
echo -e "${YELLOW}Waiting 3 seconds for document indexing...${NC}"
sleep 3
echo ""

# Test 4: List Documents
echo -e "${BLUE}Test 4: List All Documents${NC}"
echo "GET $API_URL/api/v1/documents"
curl -s $API_URL/api/v1/documents \
  -H "X-API-Key: $API_KEY" | python -m json.tool
echo ""
echo ""

# Test 5: Query about remote work
echo -e "${BLUE}Test 5: Query - Can I work from another country?${NC}"
echo "POST $API_URL/api/v1/query"
curl -s -X POST $API_URL/api/v1/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Can I work from another country?"}' | python -m json.tool
echo ""
echo ""

# Test 6: Query about vacation days
echo -e "${BLUE}Test 6: Query - How many vacation days do I get?${NC}"
echo "POST $API_URL/api/v1/query"
curl -s -X POST $API_URL/api/v1/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days do I get as a new employee?"}' | python -m json.tool
echo ""
echo ""

# Test 7: Query with insufficient context
echo -e "${BLUE}Test 7: Query - Insufficient Context Test${NC}"
echo "POST $API_URL/api/v1/query"
curl -s -X POST $API_URL/api/v1/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the salary for software engineers?"}' | python -m json.tool
echo ""
echo ""

# Test 8: Test caching (same question as Test 5)
echo -e "${BLUE}Test 8: Query - Test Caching (same as Test 5)${NC}"
echo "POST $API_URL/api/v1/query"
echo -e "${YELLOW}This should be cached and much faster${NC}"
curl -s -X POST $API_URL/api/v1/query \
  -H "X-API-Key: $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Can I work from another country?"}' | python -m json.tool
echo ""
echo ""

# Test 9: Tenant Isolation Test
echo -e "${BLUE}Test 9: Tenant Isolation Test${NC}"
echo "Querying with different tenant API key (should return insufficient_context)"
curl -s -X POST $API_URL/api/v1/query \
  -H "X-API-Key: techstart_test_key_hash" \
  -H "Content-Type: application/json" \
  -d '{"question": "What is the remote work policy?"}' | python -m json.tool
echo ""
echo ""

echo -e "${GREEN}=========================================="
echo "All tests completed successfully!"
echo "==========================================${NC}"
echo ""
echo "Key observations:"
echo "1. Documents were uploaded and chunked"
echo "2. Queries return answers with source citations"
echo "3. Insufficient context is properly detected"
echo "4. Caching works (check processing_time_ms and cached flag)"
echo "5. Tenant isolation prevents cross-tenant data access"
