"""
Provider factory.
Returns the correct LLM and vector store based on settings.
"""
import logging
from functools import lru_cache
from langchain_core.language_models import BaseLanguageModel
from langchain_core.vectorstores import VectorStore
from api.config import settings

logger = logging.getLogger(__name__)

@lru_cache(maxsize=1)
def get_llm() -> BaseLanguageModel:
    """Cached LLM — initialized once, reused across requests."""
    if settings.llm_provider == "groq":
        if not settings.groq_api_key:
            raise EnvironmentError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set."
            )
        from langchain_groq import ChatGroq
        logger.info(f"Using Groq — model: {settings.groq_model}")
        return ChatGroq(
            model=settings.groq_model,
            api_key=settings.groq_api_key,
            temperature=0,
        )

    from langchain_ollama import OllamaLLM
    logger.info(f"Using Ollama — model: {settings.ollama_model}")
    return OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url,
    )


@lru_cache
def get_embeddings():
    """
    Cached embeddings.
    Uses Pinecone inference if use_pinecone_inference=true (zero local memory).
    Falls back to HuggingFace local model otherwise.
    """
    if settings.use_pinecone_inference:
        # Return None — Pinecone inference handles embeddings server-side
        logger.info("Using Pinecone inference for embeddings (no local model)")
        return None

    from langchain_huggingface import HuggingFaceEmbeddings
    logger.info(f"Loading local embeddings: {settings.embedding_model}")
    return HuggingFaceEmbeddings(model_name=settings.embedding_model)


class PineconeInferenceWrapper(VectorStore):
    """
    Vector store using Pinecone's server-side inference API.
    No local embedding model needed — zero memory cost.
    """
    def __init__(self, index, model: str, text_key: str = "text"):
        self._index = index
        self._model = model
        self._text_key = text_key

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        from langchain_core.documents import Document
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        result = pc.inference.embed(
            model=self._model,
            inputs=[query],
            parameters={"input_type": "query", "truncate": "END"},
        )
        vector = result[0].values
        results = self._index.query(vector=vector, top_k=k, include_metadata=True)
        docs = []
        for match in results.get("matches", []):
            meta = match.get("metadata", {})
            text = meta.pop(self._text_key, "")
            docs.append(Document(page_content=text, metadata=meta))
        return docs

    def add_documents(self, documents, **kwargs):
        import uuid
        from pinecone import Pinecone
        pc = Pinecone(api_key=settings.pinecone_api_key)
        texts = [d.page_content for d in documents]
        result = pc.inference.embed(
            model=self._model,
            inputs=texts,
            parameters={"input_type": "passage", "truncate": "END"},
        )
        vectors = [r.values for r in result]
        records = [
            {
                "id": str(uuid.uuid4()),
                "values": vectors[i],
                "metadata": {
                    self._text_key: texts[i],
                    **documents[i].metadata,
                },
            }
            for i in range(len(documents))
        ]
        for batch_start in range(0, len(records), 100):
            self._index.upsert(vectors=records[batch_start:batch_start + 100])
        return [r["id"] for r in records]

    @classmethod
    def from_texts(cls, texts, embedding, metadatas=None, **kwargs):
        raise NotImplementedError("Use add_documents instead.")


class PineconeVectorStoreWrapper(VectorStore):
    """Original wrapper using local embeddings."""
    def __init__(self, index, embeddings, text_key="text"):
        self._index = index
        self._embeddings = embeddings
        self._text_key = text_key

    def similarity_search(self, query: str, k: int = 4, **kwargs):
        from langchain_core.documents import Document
        vector = self._embeddings.embed_query(query)
        results = self._index.query(vector=vector, top_k=k, include_metadata=True)
        docs = []
        for match in results.get("matches", []):
            meta = match.get("metadata", {})
            text = meta.pop(self._text_key, "")
            docs.append(Document(page_content=text, metadata=meta))
        return docs

    def add_documents(self, documents, **kwargs):
        import uuid
        texts = [d.page_content for d in documents]
        vectors = self._embeddings.embed_documents(texts)
        records = [
            {
                "id": str(uuid.uuid4()),
                "values": vectors[i],
                "metadata": {
                    self._text_key: texts[i],
                    **documents[i].metadata,
                },
            }
            for i in range(len(documents))
        ]
        for batch_start in range(0, len(records), 100):
            self._index.upsert(vectors=records[batch_start:batch_start + 100])
        return [r["id"] for r in records]

    @classmethod
    def from_texts(cls, texts, embedding, metadatas=None, **kwargs):
        raise NotImplementedError("Use add_documents instead.")


@lru_cache(maxsize=1)
def get_vectorstore() -> VectorStore:
    """Cached vector store — initialized once, reused across requests."""
    if settings.vector_store_provider == "pinecone":
        if not settings.pinecone_api_key:
            raise EnvironmentError(
                "VECTOR_STORE_PROVIDER=pinecone but PINECONE_API_KEY is not set."
            )
        from pinecone import Pinecone, ServerlessSpec

        pc = Pinecone(api_key=settings.pinecone_api_key)
        existing = [i.name for i in pc.list_indexes()]

        if settings.use_pinecone_inference:
            # Pinecone inference — no local embeddings needed
            index_name = settings.pinecone_index_name
            if index_name not in existing:
                logger.info(f"Creating Pinecone index with inference: {index_name}")
                pc.create_index(
                    name=index_name,
                    dimension=1024,  # multilingual-e5-large dimension
                    metric="cosine",
                    spec=ServerlessSpec(cloud="aws", region="us-east-1"),
                )
            index = pc.Index(index_name)
            logger.info(f"Using Pinecone inference index: {index_name}")
            return PineconeInferenceWrapper(
                index=index,
                model=settings.pinecone_inference_model,
            )

        # Local embeddings fallback
        embeddings = get_embeddings()
        if settings.pinecone_index_name not in existing:
            logger.info(f"Creating Pinecone index: {settings.pinecone_index_name}")
            pc.create_index(
                name=settings.pinecone_index_name,
                dimension=384,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
        index = pc.Index(settings.pinecone_index_name)
        logger.info(f"Using Pinecone index: {settings.pinecone_index_name}")
        return PineconeVectorStoreWrapper(index=index, embeddings=embeddings)

    # Chroma fallback
    embeddings = get_embeddings()
    from langchain_chroma import Chroma
    logger.info(f"Using Chroma at: {settings.chroma_persist_dir}")
    return Chroma(
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir,
    )