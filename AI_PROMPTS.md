# AI Prompts Documentation

This document details the exact prompts used in the AI Knowledge Assistant system, including iterations, examples of accepted vs. rejected outputs, and why human judgment was required.

## System Prompt

### Final Version (v2)

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

### Iteration History

**Version 1 (Initial - Rejected)**
```
You are a helpful assistant that answers questions about company documents.
Answer based on the provided context.
```

**Problems with v1:**
- Too generic, didn't emphasize the restriction to provided context
- No explicit refusal instruction when context is insufficient
- Model sometimes hallucinated information not in the documents
- No mention of source citation requirement

**Version 2 (Current - Accepted)**
- Added "CRITICAL RULES" section with numbered requirements
- Explicit instruction to set `insufficient_context: true` when information is missing
- Emphasized "ONLY" and "MUST" to strengthen constraints
- Added professional language requirement for business context

## User Prompt Template

### Final Version

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

### Context Chunk Format

```
--- Document: {document_name} (Chunk {chunk_index}/{total_chunks}) ---
{chunk_text}
---
```

**Why this format:**
- Clear document boundaries with `---` separators
- Document name prominently displayed for citation
- Chunk index helps model understand document structure
- Clean, readable format that doesn't confuse the model

## Output Format (Structured JSON)

### Schema

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

### Why Structured JSON?

**Attempted alternatives:**
1. **Free-form text with markdown** - Rejected because parsing citations was unreliable
2. **XML format** - Rejected because OpenAI models perform better with JSON
3. **Current JSON format** - Accepted because:
   - OpenAI's `response_format: json_object` ensures valid JSON
   - Fields are predictable and type-safe
   - Easy to parse and validate
   - Supports structured data for sources array

## Example Prompts and Outputs

### Example 1: Successful Answer with Sources

**Context:**
```
--- Document: Remote Work Policy 2024.md (Chunk 1/3) ---
Employees may work remotely up to 3 days per week with manager approval.

International remote work requires HR approval and must comply with local tax laws.
Employees must submit a request at least 30 days in advance.
---

--- Document: Equipment Policy.md (Chunk 2/5) ---
The company provides laptops and monitors for remote work.
Employees are responsible for maintaining a secure home office environment.
---
```

**Question:**
```
Can I work from Spain for 2 weeks?
```

**Output (Accepted):**
```json
{
  "answer": "Yes, you can work from Spain for 2 weeks, but it requires HR approval and must comply with local tax laws. You need to submit a request at least 30 days in advance according to the Remote Work Policy.",
  "sources": [
    {
      "document_name": "Remote Work Policy 2024.md",
      "relevant_excerpt": "International remote work requires HR approval and must comply with local tax laws. Employees must submit a request at least 30 days in advance."
    }
  ],
  "confidence": 0.92,
  "insufficient_context": false
}
```

**Why accepted:**
- Answer directly addresses the question
- Cites specific policy document
- Includes relevant excerpt that supports the answer
- High confidence appropriate for clear policy statement
- Professional, concise language

### Example 2: Insufficient Context (Correct Refusal)

**Context:**
```
--- Document: Equipment Policy.md (Chunk 1/3) ---
The company provides laptops and monitors for remote work.
Employees are responsible for maintaining a secure home office environment.
---
```

**Question:**
```
What is the vacation policy for new employees?
```

**Output (Accepted):**
```json
{
  "answer": null,
  "sources": [],
  "confidence": 0.0,
  "insufficient_context": true
}
```

**Why accepted:**
- Correctly identified that context doesn't contain vacation policy information
- Set `insufficient_context: true` as required
- Didn't hallucinate or make up information
- This is the desired behavior when information is missing

### Example 3: Hallucination (Rejected)

**Context:**
```
--- Document: Remote Work Policy 2024.md (Chunk 1/3) ---
Employees may work remotely up to 3 days per week with manager approval.
---
```

**Question:**
```
How many vacation days do employees get?
```

**Output (Rejected - from v1 prompt):**
```json
{
  "answer": "Most companies offer 10-15 vacation days per year for new employees, increasing with tenure.",
  "sources": [],
  "confidence": 0.5,
  "insufficient_context": false
}
```

**Why rejected:**
- Model used external knowledge instead of provided context
- Answer is generic and not specific to the company
- Should have set `insufficient_context: true`
- This behavior led to v2 prompt with stronger constraints

**After v2 prompt (Accepted):**
```json
{
  "answer": null,
  "sources": [],
  "confidence": 0.0,
  "insufficient_context": true
}
```

### Example 4: Multi-Document Synthesis

**Context:**
```
--- Document: Remote Work Policy 2024.md (Chunk 1/3) ---
Employees may work remotely up to 3 days per week with manager approval.
Equipment must be returned when employment ends.
---

--- Document: Equipment Policy.md (Chunk 1/5) ---
The company provides laptops and monitors for remote work.
Employees must use company-provided VPN for all work activities.
---

--- Document: Security Policy.md (Chunk 2/8) ---
All devices must have full-disk encryption enabled.
VPN access requires two-factor authentication.
---
```

**Question:**
```
What equipment and security requirements do I need for remote work?
```

**Output (Accepted):**
```json
{
  "answer": "For remote work, the company provides laptops and monitors. You must use the company-provided VPN with two-factor authentication for all work activities. Additionally, all devices must have full-disk encryption enabled to meet security requirements.",
  "sources": [
    {
      "document_name": "Equipment Policy.md",
      "relevant_excerpt": "The company provides laptops and monitors for remote work. Employees must use company-provided VPN for all work activities."
    },
    {
      "document_name": "Security Policy.md",
      "relevant_excerpt": "All devices must have full-disk encryption enabled. VPN access requires two-factor authentication."
    }
  ],
  "confidence": 0.88,
  "insufficient_context": false
}
```

**Why accepted:**
- Successfully synthesized information from multiple documents
- Cited both relevant sources
- Provided comprehensive answer covering equipment and security
- Maintained professional tone
- Appropriate confidence level for multi-source answer

## When Human Judgment Was Required

### 1. Defining "Insufficient Context"

**Challenge:** What threshold constitutes "insufficient context"?

**Examples requiring judgment:**
- **Partial information**: Context mentions "vacation policy exists" but doesn't give details
  - **Decision**: Treat as insufficient context; don't make partial guesses
- **Implicit information**: Context says "standard benefits apply" without defining "standard"
  - **Decision**: Treat as insufficient context; don't assume definitions
- **Outdated information**: Context has 2023 policy but question asks about 2024
  - **Decision**: Provide 2023 information with caveat in answer

**Prompt refinement:** Added explicit instruction to prefer refusal over speculation

### 2. Source Citation Granularity

**Challenge:** How specific should source excerpts be?

**Initial behavior:** Model sometimes cited entire paragraphs (200+ words)
**Desired behavior:** Cite 1-2 key sentences that directly support the answer

**Solution:** Added "Brief quote" instruction in prompt template
**Human judgment:** Reviewed outputs and adjusted prompt wording to get concise excerpts

### 3. Confidence Score Calibration

**Challenge:** Model's confidence scores were inconsistent

**Observations:**
- Simple, single-source answers: Model gave 0.95-0.99 (too high)
- Multi-source synthesis: Model gave 0.6-0.7 (appropriate)
- Ambiguous context: Model gave 0.8+ (too high)

**Human judgment decisions:**
- Reviewed 50+ sample outputs
- Defined guidelines: 0.9+ for clear single-source, 0.7-0.9 for multi-source, <0.7 for ambiguous
- Considered adding few-shot examples to calibrate confidence (deferred to future work)

**Current approach:** Accept model's confidence as-is, use 0.7 threshold for filtering low-quality responses

### 4. Handling Ambiguous Questions

**Challenge:** Questions that could have multiple interpretations

**Example:**
- Question: "What's the policy?"
- Context has multiple policies (remote work, vacation, equipment)

**Initial behavior:** Model picked one policy arbitrarily
**Desired behavior:** Ask for clarification or list all relevant policies

**Solution:** Added instruction to be "complete" in answers
**Result:** Model now mentions multiple policies when question is ambiguous

**Human judgment:** Decided this is acceptable for MVP; future enhancement would detect ambiguous questions and prompt for clarification

### 5. Professional Language Calibration

**Challenge:** Balancing friendliness with professionalism

**Examples:**
- Too casual: "Yeah, you can totally work from home 3 days a week!"
- Too formal: "Pursuant to company policy document 2024-HR-001, section 3.2..."
- Just right: "You can work remotely up to 3 days per week with manager approval."

**Human judgment:** Reviewed outputs and added "professional business language" to prompt
**Result:** Model now uses appropriate tone consistently

## Prompt Engineering Lessons Learned

### What Worked

1. **Explicit constraints**: Using "ONLY" and "MUST" in all-caps significantly reduced hallucinations
2. **Structured output**: JSON schema enforcement eliminated parsing errors
3. **Example format**: Showing the exact JSON structure in the prompt improved compliance
4. **Numbered rules**: "CRITICAL RULES" with numbers made instructions more salient
5. **Negative examples**: Explicitly stating what NOT to do (e.g., "Never make assumptions")

### What Didn't Work

1. **Implicit expectations**: Assuming model would cite sources without explicit instruction
2. **Vague language**: "Try to" or "prefer to" instead of "MUST" led to inconsistent behavior
3. **Complex instructions**: Long paragraphs of instructions were less effective than bullet points
4. **Confidence without calibration**: Asking for confidence without examples led to miscalibration

### Future Improvements

1. **Few-shot examples**: Include 2-3 example Q&A pairs in system prompt to demonstrate desired behavior
2. **Chain-of-thought**: Ask model to explain reasoning before generating final answer
3. **Confidence calibration**: Provide specific examples of high/medium/low confidence scenarios
4. **Dynamic prompting**: Adjust prompt based on query complexity (simple vs. multi-document)
5. **Iterative refinement**: Implement feedback loop where low-rated answers trigger prompt adjustments

## Cost Analysis

### Token Usage per Query

**Average query:**
- System prompt: ~150 tokens
- Context (5 chunks × 500 tokens): ~2,500 tokens
- User prompt template: ~100 tokens
- Question: ~20 tokens
- **Total input**: ~2,770 tokens

**Average response:**
- Answer: ~150 tokens
- Sources (2 sources × 50 tokens): ~100 tokens
- JSON structure: ~50 tokens
- **Total output**: ~300 tokens

**Cost per query (gpt-4.1-mini):**
- Input: 2,770 tokens × $0.00015 / 1K = $0.00042
- Output: 300 tokens × $0.0006 / 1K = $0.00018
- **Total**: ~$0.0006 per query

**With caching (30% hit rate):**
- Effective cost: ~$0.00042 per query

### Optimization Opportunities

1. **Prompt compression**: Remove unnecessary whitespace and formatting (-10% tokens)
2. **Shorter system prompt**: Condense instructions (-20 tokens)
3. **Fewer chunks**: Reduce from 5 to 3 chunks when appropriate (-1,000 tokens)
4. **Streaming**: Stop generation early if answer is complete (-50 tokens output)

**Potential savings**: 15-20% cost reduction with optimizations

## Conclusion

The prompt design evolved significantly from initial version to current implementation. Key learnings include the importance of explicit constraints, structured output formats, and human review to calibrate model behavior. The current prompts achieve reliable performance with low hallucination rates and appropriate refusal behavior when context is insufficient.

Future work should focus on few-shot examples, confidence calibration, and dynamic prompt adjustment based on query complexity.