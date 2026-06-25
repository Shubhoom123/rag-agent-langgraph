"""
POST /api/query        — single-shot answer
GET  /api/query/stream — streaming Server-Sent Events answer
"""
import json
import logging
from typing import AsyncGenerator, Optional
from functools import lru_cache

from fastapi import Request
from api.middleware.security import limiter, sanitize_question
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.middleware.auth import AuthenticatedUser, get_current_user
from api.models.schemas import QueryRequest, QueryResponse, SourceDocument, TokenUsage
from api.providers import get_llm, get_vectorstore
from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@lru_cache(maxsize=1)
def _get_cached_agent():
    return _build_agent()


def _build_agent():
    from langgraph.graph import StateGraph, END
    from langchain_core.documents import Document
    from typing import TypedDict, List

    llm = get_llm()
    vectorstore = get_vectorstore()

    class GraphState(TypedDict):
        question: str
        rewritten_question: str
        generation: Optional[str]
        documents: List[Document]
        filtered_documents: List[Document]
        relevance_score: float
        retries: int
        web_search_needed: bool
        history: List[dict]
        token_usage: Optional[dict]
        user_id: Optional[str]

    def rewrite_query(state: GraphState):
        logger.info("Node: rewrite_query")
        question = state["question"]

        if len(question.split()) <= 8:
            logger.info("Short question — skipping rewrite")
            return {"rewritten_question": question}

        prompt = (
            f"Rewrite the following question as a concise search query "
            f"that preserves the original meaning and key entities. "
            f"Keep proper nouns, names, and specific terms exactly as they are. "
            f"Max 12 words.\n\n"
            f"Question: {question}\n"
            f"Search query:"
        )

        response = llm.invoke(prompt)
        rewritten = (
            response.content if hasattr(response, "content") else str(response)
        ).strip()

        if len(rewritten.split()) < 2:
            logger.warning("Rewrite too short — using original question")
            return {"rewritten_question": question}

        logger.info(f"Rewritten: '{question}' → '{rewritten}'")
        return {"rewritten_question": rewritten}

    def retrieve(state: GraphState):
        logger.info("Node: retrieve")
        query = state.get("rewritten_question") or state["question"]
        fetch_k = max(settings.top_k_documents, 3)
        user_id = state.get("user_id")

        # 1. Search user's private docs
        private_docs = []
        if user_id:
            private_docs = vectorstore.similarity_search(
                query, k=fetch_k, namespace=user_id
            )
            logger.info(f"Private docs: {len(private_docs)} from namespace={user_id!r}")

        # 2. Search shared knowledge base
        shared_docs = vectorstore.similarity_search(query, k=fetch_k)
        logger.info(f"Shared docs: {len(shared_docs)} from default namespace")

        # 3. Private docs take priority, shared fills the rest
        docs = (private_docs + shared_docs)[:fetch_k * 2]

        logger.info(f"Total docs for generation: {len(docs)}")
        return {"documents": docs}

    def grade_documents(state: GraphState):
        logger.info("Node: grade_documents")
        docs = state["documents"]
        question = state["question"]

        if not docs:
            return {
                "relevance_score": 0.0,
                "web_search_needed": True,
                "filtered_documents": [],
            }

        relevant_docs = []
        for doc in docs:
            snippet = doc.page_content[:400]
            prompt = (
                f"Does this document contain information useful for answering the question?\n\n"
                f"Question: {question}\n\n"
                f"Document:\n{snippet}\n\n"
                f"Reply with only 'yes' or 'no'."
            )
            response = llm.invoke(prompt)
            answer = (
                response.content if hasattr(response, "content") else str(response)
            ).strip().lower()

            if answer.startswith("yes"):
                relevant_docs.append(doc)

        relevance_score = len(relevant_docs) / len(docs)
        logger.info(
            f"Relevance: {len(relevant_docs)}/{len(docs)} relevant "
            f"(score: {relevance_score:.2f})"
        )

        top_relevant = relevant_docs[:3]
        web_search_needed = len(relevant_docs) == 0

        return {
            "relevance_score": relevance_score,
            "web_search_needed": web_search_needed,
            "filtered_documents": top_relevant,
        }

    def web_search_node(state: GraphState):
        logger.info("Node: web_search (Tavily)")
        retries = state.get("retries", 0) + 1
        query = state.get("rewritten_question") or state["question"]
        temp_docs = []

        try:
            from tavily import TavilyClient
            client = TavilyClient(api_key=settings.tavily_api_key)
            response = client.search(
                query=query,
                max_results=3,
                search_depth="basic",
            )
            for result in response.get("results", []):
                temp_docs.append(
                    Document(
                        page_content=result.get("content", ""),
                        metadata={
                            "source": result.get("url", "tavily"),
                            "title": result.get("title", ""),
                            "temporary": True,
                        }
                    )
                )
            logger.info(f"Tavily fetched {len(temp_docs)} results")
        except Exception as e:
            logger.warning(f"Tavily search failed: {e}")

        existing_docs = state.get("documents", [])
        all_docs = existing_docs + temp_docs
        filtered = temp_docs[:3] if temp_docs else all_docs[:3]

        return {
            "retries": retries,
            "web_search_needed": False,
            "documents": all_docs,
            "filtered_documents": filtered,
        }

    def generate(state: GraphState):
        logger.info("Node: generate")

        docs_to_use = state.get("filtered_documents") or state["documents"]
        context = "\n\n".join(d.page_content for d in docs_to_use)
        logger.info(f"Generating with {len(docs_to_use)} docs")

        history_text = ""
        if state.get("history"):
            history_lines = []
            for msg in state["history"]:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_lines.append(f"{role}: {msg['text']}")
            history_text = "\n".join(history_lines)

        prompt = (
            f"{'Conversation history:' + chr(10) + history_text + chr(10) + chr(10) if history_text else ''}"
            f"Context:\n{context}\n\n"
            f"Current question: {state['question']}\n\n"
            f"Answer the question using ONLY the context provided above. "
            f"Do not use any outside knowledge. "
            f"If the context does not contain enough information to answer, "
            f"say 'I don't have enough information in my knowledge base to answer this.' "
            f"If the question refers to something from the conversation history, "
            f"use that to understand what is being asked. "
            f"Never say 'based on my knowledge' or 'based on the context' — "
            f"just answer directly.\n\n"
            f"Answer:"
        )

        response = llm.invoke(prompt)
        text = (
            response.content if hasattr(response, "content") else str(response)
        )

        token_usage = None
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            token_usage = {
                "prompt_tokens": response.usage_metadata.get("input_tokens", 0),
                "completion_tokens": response.usage_metadata.get("output_tokens", 0),
                "total_tokens": response.usage_metadata.get("total_tokens", 0),
            }
        elif hasattr(response, "response_metadata"):
            meta = response.response_metadata.get("token_usage", {})
            token_usage = {
                "prompt_tokens": meta.get("prompt_tokens", 0),
                "completion_tokens": meta.get("completion_tokens", 0),
                "total_tokens": meta.get("total_tokens", 0),
            }

        return {
            "generation": text,
            "documents": state["documents"],
            "token_usage": token_usage,
        }

    def decide_to_generate(state: GraphState) -> str:
        if not state.get("web_search_needed", False):
            return "generate"
        if state.get("retries", 0) < settings.max_retries:
            return "web_search"
        logger.info("Max retries reached — generating with available docs")
        return "generate"

    workflow = StateGraph(GraphState)
    workflow.add_node("rewrite_query", rewrite_query)
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("web_search", web_search_node)

    workflow.set_entry_point("rewrite_query")
    workflow.add_edge("rewrite_query", "retrieve")
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {"generate": "generate", "web_search": "web_search"},
    )
    workflow.add_edge("web_search", "generate")
    workflow.add_edge("generate", END)

    return workflow.compile()


@router.post("/query", response_model=QueryResponse)
@limiter.limit("10/minute")
async def query(
    request: Request,
    body: QueryRequest,
    user: AuthenticatedUser = Depends(get_current_user),
) -> QueryResponse:
    logger.info(f"Query from user={user.uid!r}: {body.question!r}")
    body.question = sanitize_question(body.question)

    try:
        app = _get_cached_agent()
    except EnvironmentError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )

    initial_state = {
        "question": body.question,
        "rewritten_question": "",
        "generation": None,
        "documents": [],
        "filtered_documents": [],
        "relevance_score": 0.0,
        "retries": 0,
        "web_search_needed": False,
        "history": [m.model_dump() for m in body.history],
        "token_usage": None,
        "user_id": body.user_id or user.uid,
    }

    try:
        result = app.invoke(initial_state)
    except Exception as e:
        logger.error(f"Agent error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Agent failed to generate a response. Check backend logs.",
        )

    sources = [
        SourceDocument(content=doc.page_content)
        for doc in result.get("documents", [])
    ]

    token_usage = None
    raw_usage = result.get("token_usage")
    if raw_usage:
        token_usage = TokenUsage(
            prompt_tokens=raw_usage.get("prompt_tokens", 0),
            completion_tokens=raw_usage.get("completion_tokens", 0),
            total_tokens=raw_usage.get("total_tokens", 0),
        )

    return QueryResponse(
        answer=result.get("generation") or "Unable to generate an answer.",
        sources=sources,
        web_search_used=result.get("retries", 0) > 0,
        retries=result.get("retries", 0),
        session_id=body.session_id,
        token_usage=token_usage,
    )


@router.get("/query/stream")
async def query_stream(
    question: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    if not question or not question.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="question query param is required",
        )

    logger.info(f"Stream query from user={user.uid!r}: {question!r}")

    async def event_generator() -> AsyncGenerator[str, None]:
        try:
            app = _get_cached_agent()
        except EnvironmentError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        initial_state = {
            "question": question,
            "rewritten_question": "",
            "generation": None,
            "documents": [],
            "filtered_documents": [],
            "relevance_score": 0.0,
            "retries": 0,
            "web_search_needed": False,
            "history": [],
            "token_usage": None,
            "user_id": user.uid,
        }

        try:
            for event in app.stream(initial_state):
                node_name = list(event.keys())[0]
                node_data = event[node_name]

                yield f"data: {json.dumps({'event': 'node', 'node': node_name})}\n\n"

                if node_name == "generate" and node_data.get("generation"):
                    yield f"data: {json.dumps({'event': 'answer', 'text': node_data['generation']})}\n\n"

            yield f"data: {json.dumps({'event': 'done'})}\n\n"

        except Exception as e:
            logger.error(f"Stream error: {e}", exc_info=True)
            yield f"data: {json.dumps({'event': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )