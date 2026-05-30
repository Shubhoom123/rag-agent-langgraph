"""
GET /api/health

Checks that the LLM and vector store are reachable.
Useful for Railway/Render health checks and frontend status indicators.
"""
import logging

from fastapi import APIRouter

from api.config import settings
from api.models.schemas import HealthResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Returns the health status of all backend dependencies.
    Does NOT require auth — monitoring tools need this without a token.
    """
    llm_ok = False
    vs_ok = False

    # ------------------------------------------------------------------
    # Check LLM
    # ------------------------------------------------------------------
    try:
        if settings.llm_provider == "ollama":
            import httpx
            resp = httpx.get(
                f"{settings.ollama_base_url}/api/tags", timeout=3
            )
            llm_ok = resp.status_code == 200
        elif settings.llm_provider == "groq":
            llm_ok = bool(settings.groq_api_key)
    except Exception as e:
        logger.warning(f"LLM health check failed: {e}")

    # ------------------------------------------------------------------
    # Check Vector Store
    # ------------------------------------------------------------------
    try:
        if settings.vector_store_provider == "chroma":
            import os
            vs_ok = os.path.exists(settings.chroma_persist_dir)
        elif settings.vector_store_provider == "pinecone":
            from pinecone import Pinecone
            pc = Pinecone(api_key=settings.pinecone_api_key)
            pc.list_indexes()
            vs_ok = True
    except Exception as e:
        logger.warning(f"Vector store health check failed: {e}")

    overall = "ok" if (llm_ok and vs_ok) else "degraded"

    return HealthResponse(
        status=overall,
        llm_provider=settings.llm_provider,
        llm_reachable=llm_ok,
        vector_store_provider=settings.vector_store_provider,
        vector_store_reachable=vs_ok,
    )