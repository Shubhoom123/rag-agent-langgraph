"""
State definitions for the RAG agent graph.
"""
from typing import TypedDict, List, Optional
from langchain_core.documents import Document


class GraphState(TypedDict):
    """
    Represents the state of the RAG agent graph.
    
    Attributes:
        question: The user's question
        generation: Generated answer
        documents: Retrieved documents
        relevance_score: Score indicating document relevance
        retries: Number of retry attempts
        web_search_needed: Flag indicating if web search is needed
    """
    question: str
    generation: Optional[str]
    documents: List[Document]
    relevance_score: float
    retries: int
    web_search_needed: bool
