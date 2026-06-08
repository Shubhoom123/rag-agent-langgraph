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
        documents: List[Document]         # all retrieved docs
        filtered_documents: List[Document] # only relevant docs passed to generate
        relevance_score: float
        retries: int
        web_search_needed: bool
        history: List[dict]

    # ------------------------------------------------------------------
    # Node 1 — Query Rewriter
    # Keep the original question meaning — just extract key terms.
    # Don't rewrite short questions (≤8 words) to avoid losing intent.
    # ------------------------------------------------------------------
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

        # Safety: if rewrite looks wrong (too short or garbled), use original
        if len(rewritten.split()) < 2:
            logger.warning("Rewrite too short — using original question")
            return {"rewritten_question": question}

        logger.info(f"Rewritten: '{question}' → '{rewritten}'")
        return {"rewritten_question": rewritten}

    # ------------------------------------------------------------------
    # Node 2 — Retrieve
    # Fetch more docs than needed (k=6) so grading has more to filter.
    # Better recall → grader picks the best → generate gets clean context.
    # ------------------------------------------------------------------
    def retrieve(state: GraphState):
        logger.info("Node: retrieve")
        query = state.get("rewritten_question") or state["question"]
        # Retrieve double the configured k so grading has more to work with
        fetch_k = max(settings.top_k_documents * 2, 6)
        docs = vectorstore.similarity_search(query, k=fetch_k)
        logger.info(f"Retrieved {len(docs)} candidate docs")
        return {"documents": docs}

    # ------------------------------------------------------------------
    # Node 3 — Grade Documents
    # Grade each doc individually, keep only relevant ones in
    # filtered_documents. Generate uses filtered_documents, not all docs.
    # This is the key fix: don't pass bad context to the LLM.
    # ------------------------------------------------------------------
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

        # Limit to top 3 relevant docs for generation — avoid token overflow
        top_relevant = relevant_docs[:3]
        web_search_needed = len(relevant_docs) == 0

        return {
            "relevance_score": relevance_score,
            "web_search_needed": web_search_needed,
            "filtered_documents": top_relevant,
        }

    # ------------------------------------------------------------------
    # Node 4 — Web Search + Wikipedia
    # Docs stored in state only — NOT written to Pinecone
    # ------------------------------------------------------------------
    def web_search_node(state: GraphState):
        logger.info("Node: web_search")
        retries = state.get("retries", 0) + 1
        query = state.get("rewritten_question") or state["question"]
        temp_docs = []

        # Source 1 — Wikipedia
        try:
            import wikipedia
            import time

            wikipedia.set_user_agent(
                "RAGAgent/1.0 (educational project; contact via github)"
            )

            search_results = wikipedia.search(query, results=2)
            wiki_docs = []

            for title in search_results[:2]:
                try:
                    page = wikipedia.page(title, auto_suggest=False)
                    wiki_docs.append(
                        Document(
                            page_content=page.content[:1500],
                            metadata={
                                "source": f"wikipedia:{title}",
                                "url": page.url,
                                "temporary": True,
                            }
                        )
                    )
                    time.sleep(0.5)
                except wikipedia.DisambiguationError as e:
                    try:
                        page = wikipedia.page(e.options[0], auto_suggest=False)
                        wiki_docs.append(
                            Document(
                                page_content=page.content[:1500],
                                metadata={
                                    "source": f"wikipedia:{e.options[0]}",
                                    "temporary": True,
                                }
                            )
                        )
                    except Exception:
                        pass
                except Exception as wiki_err:
                    logger.warning(f"Wikipedia page error: {wiki_err}")
                    continue

            if wiki_docs:
                chunks = splitter.split_documents(wiki_docs)
                temp_docs.extend(chunks)
                logger.info(f"Wikipedia fetched {len(chunks)} chunks")

        except Exception as e:
            logger.warning(f"Wikipedia search failed: {e}")

        # Source 2 — DuckDuckGo
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=2))
            ddg_docs = [
                Document(
                    page_content=f"{r['title']}\n\n{r['body']}",
                    metadata={"source": "duckduckgo", "temporary": True}
                )
                for r in results
            ]
            temp_docs.extend(ddg_docs)
            logger.info(f"DuckDuckGo fetched {len(ddg_docs)} docs")
        except Exception as e:
            logger.warning(f"DuckDuckGo failed: {e}")

        # Merge with existing Pinecone docs — temp docs NOT stored in Pinecone
        existing_docs = state.get("documents", [])
        all_docs = existing_docs + temp_docs

        # Web search results are pre-selected — treat them all as relevant
        # Cap at 3 to avoid bloating the context window
        filtered = temp_docs[:3] if temp_docs else all_docs[:3]

        return {
            "retries": retries,
            "web_search_needed": False,
            "documents": all_docs,
            "filtered_documents": filtered,
        }

    # ------------------------------------------------------------------
    # Node 5 — Generate
    # Uses filtered_documents (relevant only) — not the raw retrieved set.
    # Falls back to all documents if filtering left nothing.
    # ------------------------------------------------------------------
    def generate(state: GraphState):
        logger.info("Node: generate")

        # Prefer filtered (relevant-only) docs; fall back to all if empty
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
    # Graph — web_search now goes directly to generate
    # since docs are already in state
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
    # After web search docs are in state — go straight to generate
    workflow.add_edge("web_search", "generate")
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
        "filtered_documents": [],
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
            "filtered_documents": [],
            "relevance_score": 0.0,
            "retries": 0,
            "web_search_needed": False,
            "history": [],
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