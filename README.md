# RAG Agent with LangGraph

A production-grade self-correcting RAG system built with LangGraph, FastAPI, and React. The agent retrieves documents from a vector store, grades their relevance, and falls back to live web search when needed.

**Live Demo:** [rag-agent-langgraph.vercel.app](https://rag-agent-langgraph.vercel.app)

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + Vite, deployed on Vercel |
| Backend | FastAPI (Python), deployed on Railway |
| LLM | Groq (llama-3.1-8b-instant) / Ollama (local) |
| Vector DB | Pinecone (production) / ChromaDB (local) |
| Embeddings | sentence-transformers/all-MiniLM-L6-v2 |
| Agent Framework | LangGraph + LangChain |
| Web Search | Wikipedia API + DuckDuckGo |

---

## How It Works

The agent runs as a stateful LangGraph pipeline:

1. **Rewrite Query** — rewrites long questions into keyword search queries (skips for short ones)
2. **Retrieve** — similarity search in Pinecone
3. **Grade Documents** — LLM scores relevance of retrieved docs
4. **Web Search** (if needed) — fetches Wikipedia + DuckDuckGo results into state only, never stored in Pinecone
5. **Generate** — answers using context and full conversation history

---

## Features

- Self-correcting RAG with automatic web search fallback
- Pinecone vector store with native client (no langchain-pinecone dependency)
- Conversation memory across multi-turn chats
- Provider swapping via env vars — Groq or Ollama, Pinecone or Chroma, zero code changes
- Document ingestion via `.txt` or `.pdf` upload
- Rate limiting, prompt injection detection, and security headers
- Multi-chat UI with sidebar, search, source citations, and copy

---

## Project Structure

```
rag-agent-langgraph/
├── backend/
│   ├── api/
│   │   ├── config.py
│   │   ├── providers.py
│   │   ├── middleware/
│   │   │   ├── auth.py
│   │   │   └── security.py
│   │   ├── models/schemas.py
│   │   └── routes/
│   │       ├── health.py
│   │       ├── query.py
│   │       └── ingest.py
│   ├── scripts/
│   │   └── seed_vectorstore.py
│   ├── main.py
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── index.css
│   │   └── components/
│   │       ├── Sidebar.jsx
│   │       ├── ChatWindow.jsx
│   │       ├── Message.jsx
│   │       └── FileUpload.jsx
│   └── vite.config.js
└── README.md
```

---

## Local Development

### Prerequisites

- Python 3.11+
- Node.js 18+
- Ollama (for local LLM) or Groq API key
- Pinecone account or use ChromaDB locally

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install fastapi "uvicorn[standard]" pydantic pydantic-settings \
  python-dotenv python-multipart langgraph langchain langchain-community \
  langchain-core langchain-text-splitters langchain-ollama langchain-groq \
  langchain-huggingface sentence-transformers langchain-chroma chromadb \
  ddgs pypdf slowapi wikipedia pinecone httpx
cp .env.example .env
uvicorn main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Environment Variables

```
LLM_PROVIDER=groq
GROQ_API_KEY=your_key
GROQ_MODEL=llama-3.1-8b-instant
VECTOR_STORE_PROVIDER=pinecone
PINECONE_API_KEY=your_key
PINECONE_INDEX_NAME=rag-agent
REQUIRE_AUTH=false
REQUIRE_API_KEY=false
CORS_ORIGINS=http://localhost:5173
MAX_RETRIES=2
RELEVANCE_THRESHOLD=0.7
TOP_K_DOCUMENTS=2
```

### Seed the Vector Store

```bash
cd backend
python scripts/seed_vectorstore.py
```

---

## API

| Method | Endpoint | Description |
|---|---|---|
| GET | /api/health | LLM and vector store status |
| POST | /api/query | Ask a question |
| GET | /api/query/stream | Streaming SSE answer |
| POST | /api/ingest | Upload .txt or .pdf |

---

## Deployment

**Backend → Railway**
1. Connect GitHub repo, set Root Directory to `backend`
2. Add env vars in Railway dashboard
3. Railway uses the Dockerfile automatically

**Frontend → Vercel**
1. Import repo, set Root Directory to `frontend`
2. Add `VITE_API_URL=https://your-railway-url.up.railway.app`
3. Deploy

---

## Design Decisions

**Why LangGraph?** The self-correction loop is a first-class conditional edge in the graph, not buried in a prompt. This makes the routing logic explicit, transparent, and easy to extend.

**Why not store web results in Pinecone?** Web results are ephemeral and query-specific. Storing them permanently pollutes the vector store over time. They live only in the current request's state.

**Why Groq?** Significantly faster inference than OpenAI for llama-3.1-8b-instant, with a generous free tier.

---

## Security

- 10 req/min rate limit per IP on /api/query
- 1MB request size limit
- Prompt injection detection
- Security headers (X-Content-Type-Options, X-Frame-Options, HSTS)
- CORS locked to production Vercel domain

---

## License

MIT