"""
Utility functions for the RAG agent.
"""
from typing import List
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_ollama import OllamaLLM
from langchain_text_splitters import RecursiveCharacterTextSplitter
from config.settings import settings


def get_embeddings():
    """Initialize and return embeddings model."""
    return HuggingFaceEmbeddings(
        model_name=settings.embedding_model
    )


def get_llm():
    """Initialize and return LLM based on configuration."""
    return OllamaLLM(
        model=settings.ollama_model,
        base_url=settings.ollama_base_url
    )


def get_vectorstore(embeddings=None):
    """Initialize and return vector store."""
    if embeddings is None:
        embeddings = get_embeddings()
    
    return Chroma(
        embedding_function=embeddings,
        persist_directory=settings.chroma_persist_dir
    )


def load_documents(file_path: str) -> List[Document]:
    """Load and split documents from a file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len
    )
    
    chunks = text_splitter.split_text(text)
    documents = [Document(page_content=chunk) for chunk in chunks]
    
    return documents


def format_documents(documents: List[Document]) -> str:
    """Format documents into a single string."""
    return "\n\n".join([doc.page_content for doc in documents])
