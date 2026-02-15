"""LLM and embedding service using OpenAI."""
from typing import List, Dict, Any
from openai import OpenAI
import tiktoken
import json
from config import settings


class LLMService:
    """OpenAI LLM service for embeddings and completions."""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.tokenizer = tiktoken.encoding_for_model("gpt-4")
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text."""
        return len(self.tokenizer.encode(text))
    
    def chunk_text(self, text: str) -> List[Dict[str, Any]]:
        """Chunk text into smaller pieces with overlap."""
        tokens = self.tokenizer.encode(text)
        chunks = []
        
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap
        
        for i in range(0, len(tokens), chunk_size - overlap):
            chunk_tokens = tokens[i:i + chunk_size]
            chunk_text = self.tokenizer.decode(chunk_tokens)
            
            # Try to preserve sentence boundaries
            if i + chunk_size < len(tokens):
                last_period = chunk_text.rfind('.')
                if last_period > chunk_size * 0.7:
                    chunk_text = chunk_text[:last_period + 1]
            
            chunks.append({
                'text': chunk_text,
                'index': len(chunks),
                'token_count': len(chunk_tokens)
            })
        
        return chunks
    
    async def embed_text(self, text: str) -> List[float]:
        """Generate embedding for text."""
        response = self.client.embeddings.create(
            model=settings.embedding_model,
            input=text
        )
        return response.data[0].embedding
    
    async def embed_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Generate embeddings for multiple chunks."""
        texts = [chunk['text'] for chunk in chunks]
        
        response = self.client.embeddings.create(
            model=settings.embedding_model,
            input=texts
        )
        
        for i, chunk in enumerate(chunks):
            chunk['embedding'] = response.data[i].embedding
        
        return chunks
    
    async def generate_answer(
        self,
        question: str,
        context_chunks: List[Dict[str, Any]],
        tenant_name: str = "your organization"
    ) -> Dict[str, Any]:
        """Generate answer using LLM with structured output."""
        
        # Build context from chunks
        context_parts = []
        for chunk in context_chunks:
            context_parts.append(
                f"--- Document: {chunk['document_name']} "
                f"(Chunk {chunk['chunk_index'] + 1}) ---\n"
                f"{chunk['chunk_text']}\n"
                f"---"
            )
        context = "\n\n".join(context_parts)
        
        # System prompt
        system_prompt = f"""You are an internal knowledge assistant for {tenant_name}. Your role is to answer employee questions based ONLY on the provided internal documents.

CRITICAL RULES:
1. Only use information from the provided context documents
2. Always cite your sources by referencing document names
3. If the context does not contain enough information to answer the question, you MUST respond with insufficient_context: true
4. Never make assumptions or use external knowledge
5. Be concise but complete in your answers
6. Use professional business language

Your response must be in JSON format following this exact structure."""
        
        # User prompt
        user_prompt = f"""CONTEXT DOCUMENTS:
{context}

QUESTION:
{question}

Provide your answer in the following JSON format:
{{
  "answer": "Your detailed answer here, or null if insufficient context",
  "sources": [
    {{
      "document_name": "Name of source document",
      "relevant_excerpt": "Brief quote supporting your answer"
    }}
  ],
  "confidence": 0.85,
  "insufficient_context": false
}}

Confidence should be a number between 0 and 1 indicating how well the context supports the answer.
Set insufficient_context to true if you cannot answer the question from the provided context."""
        
        # Call LLM
        response = self.client.chat.completions.create(
            model=settings.completion_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1000
        )
        
        # Parse response
        content = response.choices[0].message.content
        result = json.loads(content)
        
        # Add token usage
        result['_tokens'] = {
            'prompt': response.usage.prompt_tokens,
            'completion': response.usage.completion_tokens,
            'total': response.usage.total_tokens
        }
        
        return result


# Global LLM service instance
llm_service = LLMService()