"""
RAG correctness test.

Seeds a nonsense fact that the LLM could never know on its own,
then queries it to prove the system is grounding answers in the
vector store — not hallucinating from its own training data.

Run from backend/ directory:
    python scripts/test_rag.py

Expected result:
    ✓ Answer contains "1999" and "Mars"
    ✗ If the LLM makes up a real-world answer, RAG is broken
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain_core.documents import Document
from api.providers import get_vectorstore, get_llm

# ---------------------------------------------------------------------------
# Nonsense fact — completely fictional, LLM has no training data on this
# ---------------------------------------------------------------------------
TEST_FACT = (
    "BillCut was founded in 1999 on Mars by a team of three astronauts "
    "who wanted to help Martian colonists split utility bills fairly. "
    "The company's first product was a solar-panel cost splitter called SolarShare."
)
TEST_QUESTION = "When was BillCut founded and where?"
TEST_DOC_ID   = "billcut-test-fact"


def seed_test_fact(vectorstore):
    print("Seeding test fact into vector store...")
    doc = Document(
        page_content=TEST_FACT,
        metadata={"source": "test", "id": TEST_DOC_ID},
    )
    vectorstore.add_documents([doc])
    print(f"  ✓ Seeded: \"{TEST_FACT[:80]}...\"")


def run_rag_query(vectorstore, llm):
    print(f"\nQuerying: \"{TEST_QUESTION}\"")

    docs = vectorstore.similarity_search(TEST_QUESTION, k=3)

    print(f"\nRetrieved {len(docs)} documents:")
    for i, doc in enumerate(docs):
        print(f"  [{i+1}] {doc.page_content[:120]}...")

    context = "\n\n".join(d.page_content for d in docs)

    prompt = (
        f"Context:\n{context}\n\n"
        f"Question: {TEST_QUESTION}\n\n"
        f"Answer using ONLY the context above. "
        f"Do not use any outside knowledge. "
        f"If the context doesn't contain the answer, say so.\n\n"
        f"Answer:"
    )

    response = llm.invoke(prompt)
    answer = (
        response.content if hasattr(response, "content") else str(response)
    ).strip()

    return answer, docs


def evaluate(answer, docs):
    print(f"\nAnswer:\n  {answer}\n")

    # Check if the test doc was retrieved
    test_doc_retrieved = any(
        "BillCut" in doc.page_content for doc in docs
    )

    # Check if answer contains the nonsense facts
    answer_lower = answer.lower()
    has_year  = "1999" in answer_lower
    has_mars  = "mars" in answer_lower

    print("=" * 50)
    print("RAG CORRECTNESS TEST RESULTS")
    print("=" * 50)
    print(f"  Test doc retrieved : {'✓' if test_doc_retrieved else '✗ FAIL — wrong docs retrieved'}")
    print(f"  Answer contains year (1999) : {'✓' if has_year else '✗ FAIL'}")
    print(f"  Answer contains location (Mars) : {'✓' if has_mars else '✗ FAIL'}")

    if test_doc_retrieved and has_year and has_mars:
        print("\n✓ RAG IS WORKING CORRECTLY")
        print("  The LLM answered from the vector store, not its own knowledge.")
    else:
        print("\n✗ RAG MAY BE BROKEN")
        print("  The LLM may be answering from its own training data.")
        print("  Check: is Pinecone returning the right documents?")
    print("=" * 50)


def main():
    print("=" * 50)
    print("RAG Correctness Test — BillCut")
    print("=" * 50)

    vectorstore = get_vectorstore()
    llm = get_llm()

    seed_test_fact(vectorstore)
    answer, docs = run_rag_query(vectorstore, llm)
    evaluate(answer, docs)


if __name__ == "__main__":
    main()
