# A4. Prompt Design

## System Prompt

```
You are an internal knowledge assistant for {company_name}. Your role is to answer employee questions based ONLY on the provided internal documents.

CRITICAL RULES:
1. Only use information from the provided context documents
2. Always cite your sources by referencing document names
3. If the context does not contain enough information to answer the question, you MUST respond with insufficient_context: true
4. Never make assumptions or use external knowledge
5. Be concise but complete in your answers
6. Use professional business language

Your response must be in JSON format following this exact structure.
```

## User Prompt Template

```
CONTEXT DOCUMENTS:
{context_chunks}

QUESTION:
{user_question}

Provide your answer in the following JSON format:
{
  "answer": "Your detailed answer here, or null if insufficient context",
  "sources": [
    {
      "document_name": "Name of source document",
      "relevant_excerpt": "Brief quote supporting your answer"
    }
  ],
  "confidence": 0.85,
  "insufficient_context": false
}

Confidence should be a number between 0 and 1 indicating how well the context supports the answer.
Set insufficient_context to true if you cannot answer the question from the provided context.
```

## Context Chunk Format

```
--- Document: {document_name} (Chunk {chunk_index}/{total_chunks}) ---
{chunk_text}
---
```

## Output Format (Structured JSON)

```json
{
  "answer": "string | null",
  "sources": [
    {
      "document_name": "string",
      "relevant_excerpt": "string"
    }
  ],
  "confidence": 0.0,
  "insufficient_context": false
}
```

### Field Descriptions

- **answer**: The complete answer to the user's question, or `null` if insufficient context
- **sources**: Array of source documents with relevant excerpts that support the answer
- **confidence**: Float between 0.0 and 1.0 indicating answer reliability based on context quality
- **insufficient_context**: Boolean flag, `true` when the context doesn't contain enough information

## Why This Structure?

### Structured JSON Output
Using structured JSON (via OpenAI's response format or JSON mode) ensures:
- **Parsability**: Responses are always valid JSON, no need for regex parsing
- **Type Safety**: Fields have predictable types for downstream processing
- **Error Handling**: Missing fields or malformed responses are caught immediately
- **API Integration**: JSON responses can be directly consumed by frontend or other services

### Source Citation
Requiring explicit source citations:
- **Trustworthiness**: Users can verify answers by checking original documents
- **Accountability**: Prevents hallucination by forcing the model to ground answers in provided text
- **Audit Trail**: Sources are stored in database for compliance and quality review

### Confidence Score
The confidence field enables:
- **Threshold Filtering**: Reject low-confidence answers (e.g., < 0.6) automatically
- **UI Indicators**: Show users when answers are uncertain
- **Quality Metrics**: Track average confidence over time to measure system performance

### Insufficient Context Flag
Explicit refusal mechanism:
- **Prevents Hallucination**: Model is trained to say "I don't know" rather than guess
- **User Trust**: Clear indication when the system cannot help
- **Data Gap Detection**: Identifies missing documentation that should be added

## Example Prompt Execution

### Input
```
CONTEXT DOCUMENTS:
--- Document: Remote Work Policy 2024.md (Chunk 1/3) ---
Employees may work remotely up to 3 days per week with manager approval. 
International remote work requires HR approval and must comply with local tax laws.
---

--- Document: Travel Expense Policy.md (Chunk 2/5) ---
All international travel must be pre-approved by the finance department.
Reimbursement requires receipts and submission within 30 days.
---

QUESTION:
Can I work from Spain for 2 weeks?

Provide your answer in the following JSON format:
{...}
```

### Output
```json
{
  "answer": "Working from Spain for 2 weeks requires HR approval according to the Remote Work Policy. International remote work must comply with local tax laws. You should contact HR to discuss the specifics of your situation and ensure compliance with both company policy and Spanish regulations.",
  "sources": [
    {
      "document_name": "Remote Work Policy 2024.md",
      "relevant_excerpt": "International remote work requires HR approval and must comply with local tax laws."
    }
  ],
  "confidence": 0.82,
  "insufficient_context": false
}
```

## Prompt Iteration Strategy

### Version 1 (Initial)
- Basic system prompt without explicit refusal instruction
- **Problem**: Model sometimes hallucinated answers when context was insufficient

### Version 2 (Current)
- Added "CRITICAL RULES" section with explicit refusal requirement
- Added `insufficient_context` field to output format
- **Result**: Model now reliably refuses to answer when context is missing

### Future Improvements (with more time)
1. **Few-shot examples**: Include 2-3 example Q&A pairs in the system prompt to demonstrate desired behavior
2. **Chain-of-thought**: Ask model to explain reasoning before generating final answer
3. **Multi-turn refinement**: Allow follow-up questions to clarify ambiguous answers
4. **Dynamic prompt tuning**: Adjust prompt based on query complexity (simple vs. multi-document questions)