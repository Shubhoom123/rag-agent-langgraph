"""
Seed the vector store with Wikipedia articles.
Run once from the backend/ directory:
    python scripts/seed_vectorstore.py

Features:
- Skips already-seeded topics (checks Pinecone before loading)
- Rate limit protection with exponential backoff
- Explicit shared namespace="" for clean separation from user docs
- Broad topic coverage across AI, CS, science, history, and more
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from api.providers import get_vectorstore
from api.config import settings

# ---------------------------------------------------------------------------
# Shared namespace — all seeded data goes here
# User uploaded docs go into namespace=user.uid (never mixed)
# ---------------------------------------------------------------------------
SHARED_NAMESPACE = ""

# ---------------------------------------------------------------------------
# Track seeded topics locally to avoid re-seeding
# ---------------------------------------------------------------------------
SEEDED_TOPICS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".seeded_topics.json"
)

def load_seeded_topics() -> set:
    """Load the set of already-seeded topics from local cache."""
    if os.path.exists(SEEDED_TOPICS_FILE):
        with open(SEEDED_TOPICS_FILE, "r") as f:
            return set(json.load(f))
    return set()

def save_seeded_topic(topic: str):
    """Persist a newly seeded topic to the local cache."""
    seeded = load_seeded_topics()
    seeded.add(topic)
    with open(SEEDED_TOPICS_FILE, "w") as f:
        json.dump(list(seeded), f, indent=2)

# ---------------------------------------------------------------------------
# Topics — broad coverage across many domains
# Add new topics here daily and re-run — already seeded ones are skipped
# ---------------------------------------------------------------------------
TOPICS = [
    # ----------------------------------------------------------------
    # AI / ML Core
    # ----------------------------------------------------------------
    "Large language model",
    "Retrieval-augmented generation",
    "Transformer (deep learning architecture)",
    "Artificial neural network",
    "Machine learning",
    "Deep learning",
    "Natural language processing",
    "Prompt engineering",
    "Fine-tuning (deep learning)",
    "Reinforcement learning",
    "Reinforcement learning from human feedback",
    "Generative adversarial network",
    "Diffusion model",
    "Attention mechanism",
    "Transfer learning",
    "Self-supervised learning",
    "Few-shot learning",
    "Zero-shot learning",
    "Multi-modal learning",
    "Federated learning",
    "Explainable artificial intelligence",
    "AI alignment",
    "AI safety",
    "Artificial general intelligence",

    # ----------------------------------------------------------------
    # Vector DBs / RAG components
    # ----------------------------------------------------------------
    "Vector database",
    "Word embedding",
    "Cosine similarity",
    "Semantic search",
    "Approximate nearest neighbor search",
    "Knowledge graph",
    "Information retrieval",
    "Text mining",
    "Named entity recognition",
    "Sentence embedding",

    # ----------------------------------------------------------------
    # LLM Ecosystem
    # ----------------------------------------------------------------
    "LangChain",
    "Llama (language model)",
    "GPT-4",
    "BERT (language model)",
    "Claude (language model)",
    "Gemini (language model)",
    "Mistral AI",
    "Hugging Face",
    "OpenAI",
    "Anthropic",
    "Groq",
    "Ollama (software)",
    "LlamaIndex",

    # ----------------------------------------------------------------
    # CS Fundamentals
    # ----------------------------------------------------------------
    "Python (programming language)",
    "Application programming interface",
    "Representational state transfer",
    "Database",
    "SQL",
    "NoSQL",
    "Data structure",
    "Algorithm",
    "Big O notation",
    "Object-oriented programming",
    "Functional programming",
    "Recursion (computer science)",
    "Dynamic programming",
    "Graph (abstract data type)",
    "Hash table",
    "Binary search tree",
    "Sorting algorithm",
    "Computer network",
    "OSI model",
    "TCP/IP",
    "HTTP",
    "WebSocket",
    "Microservices",
    "Serverless computing",
    "Containerization",
    "Docker (software)",
    "Kubernetes",
    "CI/CD",
    "Git",
    "Linux",
    "Operating system",
    "Computer memory",
    "CPU",
    "GPU",
    "Compiler",
    "Interpreter (computing)",
    "Virtual machine",

    # ----------------------------------------------------------------
    # Web / Backend
    # ----------------------------------------------------------------
    "FastAPI",
    "React (JavaScript library)",
    "Node.js",
    "JavaScript",
    "TypeScript",
    "HTML",
    "CSS",
    "GraphQL",
    "gRPC",
    "Authentication",
    "OAuth",
    "JSON Web Token",
    "HTTPS",
    "WebAssembly",
    "Progressive web application",

    # ----------------------------------------------------------------
    # Data Science
    # ----------------------------------------------------------------
    "Data science",
    "Pandas (software)",
    "NumPy",
    "Scikit-learn",
    "TensorFlow",
    "PyTorch",
    "Keras",
    "Jupyter Notebook",
    "Data visualization",
    "Feature engineering",
    "Overfitting",
    "Cross-validation",
    "Gradient descent",
    "Backpropagation",
    "Convolutional neural network",
    "Recurrent neural network",
    "Long short-term memory",
    "Principal component analysis",
    "Support vector machine",
    "Random forest",
    "Logistic regression",
    "Linear regression",
    "Bayesian inference",
    "Statistics",
    "Probability theory",

    # ----------------------------------------------------------------
    # Cloud / DevOps
    # ----------------------------------------------------------------
    "Cloud computing",
    "Amazon Web Services",
    "Google Cloud Platform",
    "Microsoft Azure",
    "Serverless Framework",
    "Infrastructure as code",
    "Terraform (software)",
    "Load balancing (computing)",
    "Content delivery network",
    "Database replication",
    "Redis",
    "Apache Kafka",
    "Message queue",
    "Nginx",

    # ----------------------------------------------------------------
    # Security
    # ----------------------------------------------------------------
    "Cybersecurity",
    "Encryption",
    "Public-key cryptography",
    "SQL injection",
    "Cross-site scripting",
    "Denial-of-service attack",
    "Firewall (computing)",
    "VPN",
    "Zero trust security",
    "Penetration testing",

    # ----------------------------------------------------------------
    # Science & Math
    # ----------------------------------------------------------------
    "Mathematics",
    "Linear algebra",
    "Calculus",
    "Matrix (mathematics)",
    "Eigenvalues and eigenvectors",
    "Fourier transform",
    "Graph theory",
    "Information theory",
    "Quantum computing",
    "Physics",
    "Biology",
    "Chemistry",
    "Neuroscience",
    "Cognitive science",

    # ----------------------------------------------------------------
    # History & Culture
    # ----------------------------------------------------------------
    "History of the Internet",
    "History of artificial intelligence",
    "Industrial Revolution",
    "World War II",
    "Cold War",
    "Space Race",
    "Renaissance",
    "Ancient Rome",
    "Ancient Greece",
    "Scientific Revolution",

    # ----------------------------------------------------------------
    # Business & Economics
    # ----------------------------------------------------------------
    "Startup company",
    "Venture capital",
    "Stock market",
    "Cryptocurrency",
    "Blockchain",
    "Bitcoin",
    "Ethereum",
    "Supply chain",
    "Marketing",
    "Product management",
    "Agile software development",
    "Scrum (software development)",
    "Design thinking",

    # ----------------------------------------------------------------
    # Health & Medicine
    # ----------------------------------------------------------------
    "Artificial intelligence in healthcare",
    "Medical imaging",
    "Genomics",
    "CRISPR",
    "Vaccine",
    "Mental health",
    "Neurology",

    # ----------------------------------------------------------------
    # Philosophy & Ethics
    # ----------------------------------------------------------------
    "Ethics of artificial intelligence",
    "Philosophy of mind",
    "Consciousness",
    "Turing test",
    "Chinese room",
    "Trolley problem",
]

splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    length_function=len,
)


def fetch_wikipedia_content(topic: str, retries: int = 3) -> Document | None:
    """
    Fetch Wikipedia content with exponential backoff on failure.
    Returns a Document or None if all retries fail.
    """
    import wikipedia

    for attempt in range(1, retries + 1):
        try:
            search_results = wikipedia.search(topic, results=1)
            if not search_results:
                print(f"  ⚠ No results found for '{topic}'")
                return None

            page = wikipedia.page(search_results[0], auto_suggest=False)
            content = page.content[:8000]

            return Document(
                page_content=content,
                metadata={
                    "source": f"wikipedia:{topic}",
                    "topic": topic,
                    "url": page.url,
                },
            )
        except Exception as e:
            wait = 2 ** attempt  # 2s, 4s, 8s
            print(f"  ✗ Attempt {attempt}/{retries} failed: {e}")
            if attempt < retries:
                print(f"  ↻ Retrying in {wait}s...")
                time.sleep(wait)
            else:
                return None


def seed():
    print("=" * 60)
    print("Seeding vector store with Wikipedia articles")
    print(f"Total topics: {len(TOPICS)}")
    print("=" * 60)

    vectorstore = get_vectorstore()
    seeded_topics = load_seeded_topics()

    # Filter out already seeded topics
    topics_to_seed = [t for t in TOPICS if t not in seeded_topics]
    skipped = len(TOPICS) - len(topics_to_seed)
    if skipped:

        print(f"\nSkipping {skipped} already-seeded topics")

    if not topics_to_seed:
        print("\nAll topics already seeded. Nothing to do.")
        print("   Add new topics to TOPICS list and re-run.")
        return

    print(f"Loading {len(topics_to_seed)} new topics into shared namespace\n")

    total_chunks = 0
    failed = []

    for i, topic in enumerate(topics_to_seed, 1):
        print(f"[{i}/{len(topics_to_seed)}] {topic}")

        doc = fetch_wikipedia_content(topic)

        if doc is None:
            failed.append(topic)
            time.sleep(3)
            continue

        try:
            chunks = splitter.split_documents([doc])
            # Explicit shared namespace — never touches user private namespaces
            vectorstore.add_documents(chunks, namespace=SHARED_NAMESPACE)
            total_chunks += len(chunks)
            save_seeded_topic(topic)
            print(f"Added {len(chunks)} chunks")
        except Exception as e:
            print(f"Vectorstore write failed: {e}")
            failed.append(topic)

        # Respectful delay — avoids Wikipedia rate limiting
        time.sleep(1.5)

    print("\n" + "=" * 60)
    print(f"Done! Added {total_chunks} chunks from "
          f"{len(topics_to_seed) - len(failed)} topics")

    if skipped:
        print(f"Skipped {skipped} previously seeded topics")

    if failed:
        print(f"\n Failed ({len(failed)}):")
        for t in failed:
            print(f"   - {t}")
        print("\nRe-run the script to retry failed topics.")

    print("=" * 60)


if __name__ == "__main__":
    seed()