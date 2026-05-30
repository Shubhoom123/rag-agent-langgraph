"""
POST /api/query        — single-shot answer
GET  /api/query/stream — streaming Server-Sent Events answer
"""
import json
import logging
from typing import AsyncGenerator, Optional

from fastapi import Request
from api.middleware.security import limiter, sanitize_question
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from api.middleware.auth import AuthenticatedUser, get_current_user
from api.models.schemas import QueryRequest, QueryResponse, SourceDocument
from api.providers import get_llm, get_vectorstore
from api.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


def _build_agent():
    from langgraph.graph import StateGraph, END
    from langchain_core.documents import Document
    from langchain_text_splitters import RecursiveCharacterTextSplitter
    from typing import TypedDict, List

    llm = get_llm()
    vectorstore = get_vectorstore()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
    )

    class GraphState(TypedDict):
        question: str
        rewritten_question: str
        generation: Optional[str]
        documents: List[Document]
        relevance_score: float
        retries: int
        web_search_needed: bool
        history: List[dict]

    # ------------------------------------------------------------------
    # Node 1 — Query Rewriter
    # ------------------------------------------------------------------
    def rewrite_query(state: GraphState):
        logger.info("Node: rewrite_query")
        question = state["question"]

        # Skip rewrite for short simple questions
        if len(question.split()) <= 6:
            logger.info("Short question — skipping rewrite")
            return {"rewritten_question": question}

        prompt = (
            f"Convert to a search query (max 10 words, keywords only):\n"
            f"{question}\n"
            f"Query:"
        )

        response = llm.invoke(prompt)
        rewritten = (
            response.content if hasattr(response, "content") else str(response)
        ).strip()

        logger.info(f"Rewritten: '{question}' → '{rewritten}'")
        return {"rewritten_question": rewritten}

    # ------------------------------------------------------------------
    # Node 2 — Retrieve
    # ------------------------------------------------------------------
    def retrieve(state: GraphState):
        logger.info("Node: retrieve")
        query = state.get("rewritten_question") or state["question"]
        docs = vectorstore.similarity_search(
            query, k=settings.top_k_documents
        )
        return {"documents": docs}

    # ------------------------------------------------------------------
    # Node 3 — Grade Documents
    # ------------------------------------------------------------------
    def grade_documents(state: GraphState):
        logger.info("Node: grade_documents")
        docs = state["documents"]
        question = state["question"]

        if not docs:
            return {"relevance_score": 0.0, "web_search_needed": True}

        docs_text = "\n".join(
            f"[{i+1}] {doc.page_content[:150]}"
            for i, doc in enumerate(docs)
        )

        prompt = (
            f"Question: {question}\n"
            f"Documents:\n{docs_text}\n"
            f"How many documents (0-{len(docs)}) are relevant? "
            f"Reply with one number only."
        )

        response = llm.invoke(prompt)
        score_str = (
            response.content if hasattr(response, "content") else str(response)
        ).strip()

        try:
            relevant_count = int(score_str[0])
        except (ValueError, IndexError):
            relevant_count = 0

        relevance_score = relevant_count / len(docs)
        logger.info(
            f"Relevance: {relevant_count}/{len(docs)} "
            f"(score: {relevance_score:.2f})"
        )

        return {
            "relevance_score": relevance_score,
            "web_search_needed": relevance_score < settings.relevance_threshold,
        }

    # ------------------------------------------------------------------
    # Node 4 — Web Search + Wikipedia
    # ------------------------------------------------------------------
    def web_search_node(state: GraphState):
        logger.info("Node: web_search")
        retries = state.get("retries", 0) + 1
        query = state.get("rewritten_question") or state["question"]

        # ------------------------------------------------------------------
        # Source 1 — Wikipedia (structured, reliable)
        # ------------------------------------------------------------------
        try:
            import wikipedia
            import time

            search_results = wikipedia.search(query, results=2)
            wiki_docs = []

            for title in search_results[:2]:
                try:
                    page = wikipedia.page(title, auto_suggest=False)
                    content = page.content[:1500]
                    wiki_docs.append(
                        Document(
                            page_content=content,
                            metadata={
                                "source": f"wikipedia:{title}",
                                "url": page.url,
                            }
                        )
                    )
                    time.sleep(0.3)
                except Exception:
                    continue

            if wiki_docs:
                chunks = splitter.split_documents(wiki_docs)
                vectorstore.add_documents(chunks)
                logger.info(f"Wikipedia added {len(chunks)} chunks")

        except Exception as e:
            logger.warning(f"Wikipedia search failed: {e}")

        # ------------------------------------------------------------------
        # Source 2 — DuckDuckGo (fallback for recent/niche topics)
        # ------------------------------------------------------------------
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=2))
            web_docs = [
                Document(page_content=f"{r['title']}\n\n{r['body']}")
                for r in results
            ]
            if web_docs:
                vectorstore.add_documents(web_docs)
                logger.info(f"DuckDuckGo added {len(web_docs)} documents")
        except Exception as e:
            logger.warning(f"DuckDuckGo search failed: {e}")

        return {"retries": retries, "web_search_needed": False}

    # ------------------------------------------------------------------
    # Node 5 — Generate
    # ------------------------------------------------------------------
    def generate(state: GraphState):
        logger.info("Node: generate")

        context = "\n\n".join(
            d.page_content[:200] for d in state["documents"]
        )

        # Build conversation history string
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
            f"Answer the question clearly and concisely. "
            f"Use the context if relevant, otherwise use your own knowledge. "
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
        return {"generation": text, "documents": state["documents"]}

    # ------------------------------------------------------------------
    # Routing
    # ------------------------------------------------------------------
    def decide_to_generate(state: GraphState) -> str:
        if not state.get("web_search_needed", False):
            return "generate"
        if state.get("retries", 0) < settings.max_retries:
            return "web_search"
        logger.info("Max retries reached — generating with available docs")
        return "generate"

    # ------------------------------------------------------------------
    # Graph
    # ------------------------------------------------------------------
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
    workflow.add_edge("web_search", "retrieve")
    workflow.add_edge("generate", END)

    return workflow.compile()


# ---------------------------------------------------------------------------
# POST /api/query
# ---------------------------------------------------------------------------
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
        app = _build_agent()
    except EnvironmentError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(e)
        )

    initial_state = {
        "question": body.question,
        "rewritten_question": "",
        "generation": None,
        "documents": [],
        "relevance_score": 0.0,
        "retries": 0,
        "web_search_needed": False,
        "history": [m.model_dump() for m in body.history],
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

    return QueryResponse(
        answer=result.get("generation") or "Unable to generate an answer.",
        sources=sources,
        web_search_used=result.get("retries", 0) > 0,
        retries=result.get("retries", 0),
        session_id=body.session_id,
    )


# ---------------------------------------------------------------------------
# GET /api/query/stream
# ---------------------------------------------------------------------------
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
            app = _build_agent()
        except EnvironmentError as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        initial_state = {
            "question": question,
            "rewritten_question": "",
            "generation": None,
            "documents": [],
            "relevance_score": 0.0,
            "retries": 0,
            "web_search_needed": False,
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