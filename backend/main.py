"""
FastAPI backend for RAG Agent.
Entry point for the application.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.routes import query, ingest, health
from api.config import settings
from api.middleware.security import (
    limiter,
    add_security_headers,
    add_request_id,
    limit_request_size,
    security_logger,
)

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup validation runs here
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting RAG Agent API...")
    logger.info(f"LLM provider      : {settings.llm_provider}")
    logger.info(f"Vector store      : {settings.vector_store_provider}")
    logger.info(f"Auth required     : {settings.require_auth}")
    logger.info(f"API key required  : {settings.require_api_key}")
    logger.info(f"Security logging  : {settings.log_security_events}")
    
    # Warm up — initialize cached objects at startup
    try:
        from api.providers import get_llm, get_vectorstore
        from api.routes.query import _get_cached_agent
        logger.info("Warming up LLM...")
        get_llm()
        logger.info("Warming up vector store...")
        get_vectorstore()
        logger.info("Warming up agent...")
        _get_cached_agent()
        logger.info("Warmup complete.")
    except Exception as e:
        logger.warning(f"Warmup failed (non-fatal): {e}")
    
    yield
    logger.info("Shutting down RAG Agent API...")



# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RAG Agent API",
    description="Self-correcting RAG agent with LangGraph",
    version="1.0.0",
    lifespan=lifespan,
    # Hide Swagger UI when auth is enabled in production
    docs_url="/docs" if not settings.require_auth else None,
    redoc_url=None,
)

# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True if "*" not in settings.allowed_origins else False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

# ---------------------------------------------------------------------------
# Custom middleware — order matters, runs bottom to top
# ---------------------------------------------------------------------------
app.middleware("http")(add_security_headers)
app.middleware("http")(add_request_id)
app.middleware("http")(limit_request_size)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(query.router,  prefix="/api", tags=["query"])
app.include_router(ingest.router, prefix="/api", tags=["ingest"])