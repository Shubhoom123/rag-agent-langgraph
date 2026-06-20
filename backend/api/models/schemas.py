"""
Request and response schemas for the API.
Using Pydantic v2 for validation.
"""
from typing import List, Optional
from pydantic import BaseModel, Field


# /api/query
class ChatMessage(BaseModel):
    role: str   # "user" or "assistant"
    text: str


class QueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="The question to ask the RAG agent",
    )
    history: List[ChatMessage] = Field(
        default=[],
        description="Previous messages in the conversation",
    )
    session_id: Optional[str] = Field(
        default=None,
        description="Optional session ID",
    )

    model_config = {
        "json_schema_extra": {"example": {"question": "What is LangGraph?"}}
    }


class SourceDocument(BaseModel):
    content: str = Field(..., description="Chunk of text from the source document")
    score: Optional[float] = Field(default=None, description="Relevance score")


class QueryResponse(BaseModel):
    answer: str
    sources: List[SourceDocument]
    web_search_used: bool
    retries: int
    session_id: Optional[str] = None


# /api/ingest
class IngestResponse(BaseModel):
    message: str
    chunks_added: int
    filename: str

# /api/health
class HealthResponse(BaseModel):
    status: str
    llm_provider: str
    llm_reachable: bool
    vector_store_provider: str
    vector_store_reachable: bool
    version: str = "1.0.0"