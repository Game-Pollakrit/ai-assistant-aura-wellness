# A1. Problem Framing

## Who is the user?

The primary users are **employees within a company** who need quick, accurate answers to questions about internal policies, procedures, technical documentation, and organizational knowledge. Secondary users include **HR, operations, and support teams** who manage and maintain the knowledge base.

## What decision are they trying to make?

Employees face daily decisions that require information from internal documents:

- **Policy compliance**: "What is our remote work policy for international travel?"
- **Process execution**: "How do I submit an expense report for client entertainment?"
- **Technical guidance**: "What are the approved security protocols for handling customer data?"
- **Organizational information**: "Who is responsible for vendor contract approvals?"

These decisions require **accurate, sourced information** delivered quickly to maintain productivity and ensure compliance. The cost of wrong information can range from minor inefficiency to serious compliance violations.

## Why a normal rule-based system is insufficient?

Traditional rule-based systems and keyword search fail for several critical reasons:

**Semantic understanding gap**: Employees ask questions in natural language with varying terminology. A rule-based system cannot understand that "working from abroad" and "international remote work policy" refer to the same concept. Vector-based semantic search solves this by understanding meaning, not just keywords.

**Context-dependent answers**: The same question may have different answers depending on the employee's department, role, or location. Rule-based systems cannot dynamically synthesize information from multiple documents while maintaining context. An LLM can reason across multiple sources and provide nuanced, contextual answers.

**Knowledge maintenance burden**: As policies evolve, maintaining explicit rules becomes exponentially complex. Each new document or policy change requires manual rule updates. An AI system with RAG (Retrieval-Augmented Generation) automatically incorporates new documents without rule rewriting.

**Natural language generation**: Users expect conversational, well-formatted answers with proper citations. Rule-based systems can only return pre-written templates or raw document excerpts. LLMs generate coherent, readable responses while citing specific sources for verification.

**Multi-document reasoning**: Complex questions often require synthesizing information from multiple documents (e.g., combining HR policy with finance guidelines). Rule-based systems cannot perform this cross-document reasoning effectively.

The AI-powered approach provides **semantic search** for finding relevant information, **LLM reasoning** for synthesizing answers, **source citation** for trustworthiness, and **graceful degradation** (refusing to answer when information is insufficient) rather than returning incorrect results.