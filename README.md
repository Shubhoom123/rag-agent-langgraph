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

## Deployment

**Backend → Railway**

**Frontend → Vercel**

---

## License

MIT