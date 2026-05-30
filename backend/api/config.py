"""
Backend configuration.

All secrets come from environment variables — never hardcoded.
Copy .env.example → .env and fill in your values.
"""
import os
import logging
from functools import lru_cache
from typing import List

from dotenv import load_dotenv
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

load_dotenv()
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # LLM
    # ------------------------------------------------------------------
    llm_provider: str = "ollama"

    # Ollama (local)
    ollama_model: str = "llama3.2"
    ollama_base_url: str = "http://localhost:11434"

    # Groq (production)
    groq_api_key: str = ""
    groq_model: str = "llama-3.1-8b-instant"

    # ------------------------------------------------------------------
    # Embeddings
    # ------------------------------------------------------------------
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    hf_token: str = ""

    # ------------------------------------------------------------------
    # Vector Store
    # ------------------------------------------------------------------
    vector_store_provider: str = "chroma"

    # Chroma (local)
    chroma_persist_dir: str = "./data/chroma_db"

    # Pinecone (production)
    pinecone_api_key: str = ""
    pinecone_index_name: str = "rag-agent"
    pinecone_environment: str = ""

    # ------------------------------------------------------------------
    # Firebase Auth
    # ------------------------------------------------------------------
    firebase_project_id: str = ""
    firebase_credentials_path: str = ""
    require_auth: bool = False

    # ------------------------------------------------------------------
    # API Key Auth (second layer before Firebase)
    # Set a strong random string here
    # Generate one with: python3 -c "import secrets; print(secrets.token_hex(32))"
    # ------------------------------------------------------------------
    api_key: str = ""
    require_api_key: bool = False

    # ------------------------------------------------------------------
    # Agent behaviour
    # ------------------------------------------------------------------
    max_retries: int = 2
    relevance_threshold: float = 0.7
    top_k_documents: int = 3

    # ------------------------------------------------------------------
    # CORS
    # ------------------------------------------------------------------
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    @property
    def allowed_origins(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------
    log_dir: str = "./logs"
    log_security_events: bool = True

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("llm_provider")
    @classmethod
    def validate_llm_provider(cls, v: str) -> str:
        allowed = {"ollama", "groq"}
        if v not in allowed:
            raise ValueError(f"llm_provider must be one of {allowed}, got '{v}'")
        return v

    @field_validator("vector_store_provider")
    @classmethod
    def validate_vector_store(cls, v: str) -> str:
        allowed = {"chroma", "pinecone"}
        if v not in allowed:
            raise ValueError(f"vector_store_provider must be one of {allowed}, got '{v}'")
        return v

    # ------------------------------------------------------------------
    # Startup validation — fail loudly if required keys are missing
    # ------------------------------------------------------------------
    @model_validator(mode="after")
    def validate_required_secrets(self) -> "Settings":
        errors = []

        if self.llm_provider == "groq" and not self.groq_api_key:
            errors.append(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Get a key at https://console.groq.com"
            )

        if self.vector_store_provider == "pinecone" and not self.pinecone_api_key:
            errors.append(
                "VECTOR_STORE_PROVIDER=pinecone but PINECONE_API_KEY is not set. "
                "Get a key at https://app.pinecone.io"
            )

        if self.require_auth and not self.firebase_project_id:
            errors.append(
                "REQUIRE_AUTH=true but FIREBASE_PROJECT_ID is not set."
            )

        if self.require_api_key and not self.api_key:
            errors.append(
                "REQUIRE_API_KEY=true but API_KEY is not set. "
                "Generate one with: python3 -c \"import secrets; print(secrets.token_hex(32))\""
            )

        if errors:
            error_msg = "\n".join(f"  ❌ {e}" for e in errors)
            raise ValueError(
                f"\n\nStartup failed — missing required configuration:\n{error_msg}\n"
                f"Fix these in your .env file and restart.\n"
            )

        return self

    model_config = {"case_sensitive": False}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()