"""Configuration management for the application."""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://knowledge_user:knowledge_pass@localhost:5432/knowledge_db"
    
    # Redis
    redis_url: str = "redis://localhost:6379"
    
    # Qdrant
    qdrant_url: str = "http://localhost:6333"
    
    # OpenAI
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    completion_model: str = "gpt-4.1-mini"
    
    # RAG parameters
    chunk_size: int = 500
    chunk_overlap: int = 50
    top_k_chunks: int = 5
    similarity_threshold: float = 0.7
    
    # Rate limiting
    queries_per_minute: int = 10
    queries_per_hour: int = 100
    
    # Caching
    cache_ttl_seconds: int = 3600  # 1 hour
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()