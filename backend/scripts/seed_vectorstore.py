"""
RAG Agent — Knowledge Base Seeder

Reads config from scripts/topics.json — that's the ONLY file you ever edit.

To add new topics:
    1. Open scripts/topics.json
    2. Add topics to the "curated" list
    3. Run: python scripts/seed_vectorstore.py

To increase HuggingFace articles:
    1. Change "huggingface_target" in topics.json
    2. Re-run the script

Already seeded items are always skipped — safe to restart anytime.

Run from backend/ directory:
    python scripts/seed_vectorstore.py
"""
import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from api.providers import get_vectorstore

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_FILE = os.path.join(SCRIPTS_DIR, "topics.json")
SEEDED_FILE = os.path.join(SCRIPTS_DIR, ".seeded_topics.json")
TOKEN_FILE  = os.path.join(SCRIPTS_DIR, ".token_usage.json")

# Shared namespace — seeded data lives here
# User uploaded docs go into namespace=user.uid (never mixed)
SHARED_NAMESPACE = ""

# ---------------------------------------------------------------------------
# Token budget — hard stop before Voyage AI free tier (200M)
# ---------------------------------------------------------------------------
MAX_TOKENS = 199_000_000  # Stop at 199M to stay safely under 200M limit


def estimate_tokens(texts: list) -> int:
    """Rough estimate: 1 token ≈ 4 characters (conservative)."""
    return sum(len(t) for t in texts) // 4


def load_tokens_used() -> int:
    """Load cumulative token usage from disk."""
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f).get("tokens_used", 0)
    return 0


def save_tokens_used(tokens: int):
    """Persist cumulative token usage to disk."""
    with open(TOKEN_FILE, "w") as f:
        json.dump({"tokens_used": tokens}, f, indent=2)


splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100,
    length_function=len,
)


# ---------------------------------------------------------------------------
# Config loader
# ---------------------------------------------------------------------------
def load_config() -> dict:
    """Load topics.json — the only file you ever edit."""
    if not os.path.exists(TOPICS_FILE):
        print(f"❌ topics.json not found at {TOPICS_FILE}")
        print("   Create it with: {\"curated\": [], \"huggingface_target\": 10000}")
        sys.exit(1)
    with open(TOPICS_FILE, "r") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Seeded topics tracker
# ---------------------------------------------------------------------------
def load_seeded() -> set:
    if os.path.exists(SEEDED_FILE):
        with open(SEEDED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def mark_seeded(key: str):
    seeded = load_seeded()
    seeded.add(key)
    with open(SEEDED_FILE, "w") as f:
        json.dump(list(seeded), f, indent=2)


# ---------------------------------------------------------------------------
# Wikipedia fetcher with retry
# ---------------------------------------------------------------------------
def fetch_wikipedia(topic: str, retries: int = 3) -> Document | None:
    import wikipedia

    for attempt in range(1, retries + 1):
        try:
            results = wikipedia.search(topic, results=1)
            if not results:
                print(f"  ⚠ No Wikipedia results for '{topic}'")
                return None

            page = wikipedia.page(results[0], auto_suggest=False)

            return Document(
                page_content=page.content,
                metadata={
                    "source": f"wikipedia:{topic}",
                    "topic": topic,
                    "url": page.url,
                    "type": "curated",
                },
            )
        except Exception as e:
            wait = 5 ** attempt
            print(f"  ✗ Attempt {attempt}/{retries}: {e}")
            if attempt < retries:
                print(f"  ↻ Retry in {wait}s...")
                time.sleep(wait)
    return None


# ---------------------------------------------------------------------------
# Phase 1 — Curated topics
# ---------------------------------------------------------------------------
def seed_curated(vectorstore, config: dict, seeded: set, tokens_used: int) -> tuple:
    """Returns (chunks_added, tokens_used)."""
    topics = config.get("curated", [])
    to_seed = [t for t in topics if f"curated:{t}" not in seeded]
    skipped = len(topics) - len(to_seed)

    print(f"\n{'='*60}")
    print(f"PHASE 1 — Curated Topics (full Wikipedia articles)")
    print(f"{'='*60}")
    print(f"Total: {len(topics)} | New: {len(to_seed)} | Skipped: {skipped}")
    print(f"Tokens used so far: {tokens_used:,} / {MAX_TOKENS:,}")

    if not to_seed:
        print("✅ All curated topics already seeded.")
        return 0, tokens_used

    total_chunks = 0
    failed = []

    for i, topic in enumerate(to_seed, 1):
        print(f"\n[{i}/{len(to_seed)}] {topic}")

        # Token budget check
        if tokens_used >= MAX_TOKENS:
            print(f"⚠ Token limit reached ({tokens_used:,}). Stopping to stay under 200M.")
            break

        doc = fetch_wikipedia(topic)

        if doc is None:
            failed.append(topic)
            time.sleep(3)
            continue

        try:
            chunks = splitter.split_documents([doc])
            texts = [c.page_content for c in chunks]
            estimated = estimate_tokens(texts)

            # Check if this batch would push us over the limit
            if tokens_used + estimated > MAX_TOKENS:
                print(f"  ⚠ Skipping — would exceed token limit "
                      f"({tokens_used + estimated:,} > {MAX_TOKENS:,})")
                break

            vectorstore.add_documents(chunks, namespace=SHARED_NAMESPACE)
            tokens_used += estimated
            save_tokens_used(tokens_used)
            total_chunks += len(chunks)
            mark_seeded(f"curated:{topic}")
            print(f"  ✓ {len(chunks)} chunks added | "
                  f"~{estimated:,} tokens | "
                  f"Total: {tokens_used:,}/{MAX_TOKENS:,}")

        except Exception as e:
            print(f"  ✗ Vectorstore error: {e}")
            failed.append(topic)

        time.sleep(2)

    if failed:
        print(f"\n❌ Failed ({len(failed)}): re-run to retry")
        for t in failed:
            print(f"   - {t}")

    print(f"\nPhase 1 complete: {total_chunks:,} new chunks")
    return total_chunks, tokens_used


# ---------------------------------------------------------------------------
# Phase 2 — HuggingFace Wikipedia stream
# ---------------------------------------------------------------------------
def seed_huggingface(vectorstore, config: dict, seeded: set, tokens_used: int) -> tuple:
    """Returns (chunks_added, tokens_used)."""
    target = config.get("huggingface_target", 10000)

    print(f"\n{'='*60}")
    print(f"PHASE 2 — HuggingFace Wikipedia ({target:,} articles)")
    print(f"{'='*60}")
    print(f"Tokens used so far: {tokens_used:,} / {MAX_TOKENS:,}")

    try:
        from datasets import load_dataset
    except ImportError:
        print("❌ datasets not installed. Run: pip install datasets")
        return 0, tokens_used

    already_done = len([k for k in seeded if k.startswith("hf:")])
    remaining = target - already_done

    if remaining <= 0:
        print(f"✅ Already seeded {already_done:,} HuggingFace articles. "
              f"Increase huggingface_target in topics.json to add more.")
        return 0, tokens_used

    if tokens_used >= MAX_TOKENS:
        print(f"⚠ Token limit already reached. Skipping Phase 2.")
        return 0, tokens_used

    print(f"Already seeded: {already_done:,} | Remaining: {remaining:,}")
    print("Streaming from HuggingFace... (Ctrl+C anytime to pause)\n")

    dataset = load_dataset(
        "wikimedia/wikipedia",
        "20231101.en",
        split="train",
        streaming=True,
        trust_remote_code=True,
    )

    total_chunks = 0
    processed = 0
    batch_docs = []
    BATCH_SIZE = 50

    for article in dataset:
        # Token budget check
        if tokens_used >= MAX_TOKENS:
            print(f"\n⚠ Token limit reached ({tokens_used:,}). Stopping Phase 2.")
            break

        article_id = f"hf:{article['id']}"

        if article_id in seeded:
            continue

        if len(article["text"]) < 500:
            continue

        doc = Document(
            page_content=article["text"][:15000],
            metadata={
                "source": f"wikipedia:{article['title']}",
                "topic": article["title"],
                "url": article["url"],
                "type": "huggingface",
            },
        )

        chunks = splitter.split_documents([doc])
        batch_docs.extend(chunks)

        if len(batch_docs) >= BATCH_SIZE:
            texts = [c.page_content for c in batch_docs]
            estimated = estimate_tokens(texts)

            if tokens_used + estimated > MAX_TOKENS:
                print(f"\n⚠ Batch would exceed token limit. Stopping.")
                batch_docs = []
                break

            try:
                vectorstore.add_documents(batch_docs, namespace=SHARED_NAMESPACE)
                tokens_used += estimated
                save_tokens_used(tokens_used)
                total_chunks += len(batch_docs)
                batch_docs = []
            except Exception as e:
                print(f"  ✗ Batch failed: {e}")
                batch_docs = []

        mark_seeded(article_id)
        processed += 1

        if processed % 100 == 0:
            print(f"  ✓ {processed:,}/{remaining:,} articles | "
                  f"{total_chunks:,} chunks | "
                  f"~{tokens_used:,} tokens used")

        if processed >= remaining:
            break

    # Flush remaining
    if batch_docs:
        texts = [c.page_content for c in batch_docs]
        estimated = estimate_tokens(texts)

        if tokens_used + estimated <= MAX_TOKENS:
            try:
                vectorstore.add_documents(batch_docs, namespace=SHARED_NAMESPACE)
                tokens_used += estimated
                save_tokens_used(tokens_used)
                total_chunks += len(batch_docs)
            except Exception as e:
                print(f"  ✗ Final batch failed: {e}")
        else:
            print(f"⚠ Final batch skipped — would exceed token limit.")

    print(f"\nPhase 2 complete: {processed:,} articles, {total_chunks:,} chunks")
    return total_chunks, tokens_used


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def seed():
    print("=" * 60)
    print("RAG Agent — Knowledge Base Seeder")
    print("Config: scripts/topics.json")
    print("=" * 60)

    config = load_config()
    seeded = load_seeded()
    tokens_used = load_tokens_used()

    print(f"\nConfig loaded:")
    print(f"  Curated topics      : {len(config.get('curated', []))}")
    print(f"  HuggingFace target  : {config.get('huggingface_target', 0):,}")
    print(f"  Already seeded      : {len(seeded)} items")
    print(f"  Tokens used to date : {tokens_used:,} / {MAX_TOKENS:,}")

    chunks_1, tokens_used = seed_curated(
        vectorstore=get_vectorstore(),
        config=config,
        seeded=seeded,
        tokens_used=tokens_used,
    )

    # Reload seeded after phase 1
    seeded = load_seeded()
    chunks_2, tokens_used = seed_huggingface(
        vectorstore=get_vectorstore(),
        config=config,
        seeded=seeded,
        tokens_used=tokens_used,
    )

    print(f"\n{'='*60}")
    print(f"✅ Complete!")
    print(f"   Phase 1 (curated)    : {chunks_1:,} new chunks")
    print(f"   Phase 2 (HuggingFace): {chunks_2:,} new chunks")
    print(f"   Total new            : {chunks_1 + chunks_2:,} chunks")
    print(f"   Total tokens used    : {tokens_used:,} / {MAX_TOKENS:,}")
    print(f"{'='*60}")
    print(f"\nTo add more topics: edit scripts/topics.json and re-run.")


if __name__ == "__main__":
    seed()