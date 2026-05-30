"""
Configuration settings for the RAG agent.
"""
import os
from dotenv import load_dotenv
from pydantic import BaseModel

# Load environment variables
load_dotenv()


class Settings(BaseModel):
    """Application settings."""
    
    # LLM Configuration
    llm_provider: str = os.getenv("LLM_PROVIDER", "ollama")
    ollama_model: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    ollama_base_url: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    
    # Embeddings
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
    
    # Vector Database
    chroma_persist_dir: str = os.getenv("CHROMA_PERSIST_DIR", "./data/chroma_db")
    
    # Agent Settings
    max_retries: int = int(os.getenv("MAX_RETRIES", "2"))
    relevance_threshold: float = float(os.getenv("RELEVANCE_THRESHOLD", "0.7"))
    top_k_documents: int = int(os.getenv("TOP_K_DOCUMENTS", "3"))
    
    # Hugging Face Token
    hf_token: str = os.getenv("HF_TOKEN", "")
    
    class Config:
        case_sensitive = False


# Global settings instance
settings = Settings()

# Set HF token as environment variable if provided
if settings.hf_token:
    os.environ["HF_TOKEN"] = settings.hf_token
