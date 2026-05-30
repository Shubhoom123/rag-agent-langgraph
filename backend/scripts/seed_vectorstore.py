"""
Seed the vector store with Wikipedia articles.
Run once from the backend/ directory:

    python scripts/seed_vectorstore.py

This gives the RAG agent a real knowledge base to work with
so it answers from YOUR documents instead of falling back
to web search every time.
"""
import sys
import os

# Add backend/ to path so we can import from api/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_community.document_loaders import WikipediaLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from api.providers import get_vectorstore

# ---------------------------------------------------------------------------
# Topics to load
# Add or remove topics based on what your app is about
# ---------------------------------------------------------------------------
TOPICS = [
    # AI / ML Core
    "Large language model",
    "Retrieval-augmented generation",
    "Transformer (deep learning architecture)",
    "Artificial neural network",
    "Machine learning",
    "Deep learning",
    "Natural language processing",
    "Prompt engineering",
    "Fine-tuning (deep learning)",

    # Vector DBs and RAG components
    "Vector database",
    "Word embedding",
    "Cosine similarity",
    "Semantic search",

    # LangChain ecosystem
    "LangChain",
    "Llama (language model)",
    "GPT-4",
    "BERT (language model)",

    # CS fundamentals (shows RAG works on broad topics)
    "Python (programming language)",
    "Application programming interface",
    "Representational state transfer",
    "Database",
]

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    length_function=len,
)

def seed():
    print("=" * 60)
    print("Seeding vector store with Wikipedia articles")
    print("=" * 60)

    vectorstore = get_vectorstore()
    total_chunks = 0
    failed = []

    for i, topic in enumerate(TOPICS, 1):
        print(f"\n[{i}/{len(TOPICS)}] Loading: {topic}")
        try:
            import wikipedia
            import time

            # Search for the page
            search_results = wikipedia.search(topic, results=1)
            if not search_results:
                print(f"  ⚠ No results for '{topic}'")
                failed.append(topic)
                continue

            # Get the page content directly
            page = wikipedia.page(search_results[0], auto_suggest=False)
            content = page.content[:8000]

            from langchain_core.documents import Document
            doc = Document(
                page_content=content,
                metadata={
                    "source": f"wikipedia:{topic}",
                    "topic": topic,
                    "url": page.url,
                }
            )

            chunks = splitter.split_documents([doc])
            vectorstore.add_documents(chunks)
            total_chunks += len(chunks)
            print(f"  ✓ Added {len(chunks)} chunks")

            # Small delay to avoid rate limiting
            time.sleep(2)

        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed.append(topic)
            import time
            time.sleep(3)

    print("\n" + "=" * 60)
    print(f"Done! Added {total_chunks} chunks across "
          f"{len(TOPICS) - len(failed)} topics")

    if failed:
        print(f"\nFailed topics ({len(failed)}):")
        for t in failed:
            print(f"  - {t}")

    print("=" * 60)

if __name__ == "__main__":
    seed()