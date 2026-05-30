"""
Provider factory.

Returns the correct LLM and vector store based on settings.
Swapping from Ollama → Groq or Chroma → Pinecone
is a single env var change — no code changes needed.
"""
import logging
from functools import lru_cache

from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore

from api.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# LLM
# ---------------------------------------------------------------------------
def get_llm() -> BaseLanguageModel:
    """Return LLM based on LLM_PROVIDER env var."""
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise EnvironmentError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Add it to your .env file."
            )
        from langchain_groq import ChatGroq
        logger.info(f"Using Groq — model: {settings.groq_model}")
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )

    # Default: Ollama (local)
    from langchain_ollama import OllamaLLM
    logger.info(f"Using Ollama — model: {settings.ollama_model}")
    return OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
    )


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------
@lru_cache
def get_embeddings():
    """Cached embeddings — expensive to load, reuse across requests."""
    from langchain_huggingface import HuggingFaceEmbeddings
    logger.info(f"Loading embeddings: {settings.embedding_model}")
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


# ---------------------------------------------------------------------------
# Vector Store
# ---------------------------------------------------------------------------
def get_vectorstore() -> VectorStore:
    """Return vector store based on VECTOR_STORE_PROVIDER env var."""
    embeddings = get_embeddings()

    if settings.vector_store_provider == "pinecone":
        if not settings.pinecone_api_key:
            raise EnvironmentError(
                "VECTOR_STORE_PROVIDER=pinecone but PINECONE_API_KEY is not set."
            )
        from langchain_pinecone import PineconeVectorStore
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=settings.pinecone_api_key)

        existing = [i.name for i in pc.list_indexes()]
        if settings.pinecone_index_name not in existing:
            logger.info(f"Creating Pinecone index: {settings.pinecone_index_name}")
            pc.create_index(
                name=settings.pinecone_index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )

        logger.info(f"Using Pinecone index: {settings.pinecone_index_name}")
        return PineconeVectorStore(
            index_name=settings.pinecone_index_name,
            embedding=embeddings,
            pinecone_api_key=settings.pinecone_api_key,
        )

    # Default: Chroma (local)
    from langchain_chroma import Chroma
    logger.info(f"Using Chroma at: {settings.chroma_persist_dir}")
    return Chroma(
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )