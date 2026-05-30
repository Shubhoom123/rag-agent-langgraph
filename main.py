"""
Main entry point for the RAG agent.
"""
import os
from src.agent import RAGAgent
from src.utils import get_vectorstore, load_documents


def setup_vectorstore():
    """Initialize vector store with sample documents."""
    print("Setting up vector store...")
    
    vectorstore = get_vectorstore()
    
    # Check if we have documents in data/documents/
    docs_dir = "./data/documents"
    
    if os.path.exists(docs_dir) and os.listdir(docs_dir):
        print("Loading documents from data/documents/...")
        for filename in os.listdir(docs_dir):
            if filename.endswith(".txt"):
                filepath = os.path.join(docs_dir, filename)
                documents = load_documents(filepath)
                vectorstore.add_documents(documents)
                print(f"Added {len(documents)} chunks from {filename}")
    else:
        # Add sample documents if no files exist
        print("No documents found. Adding sample documents...")
        sample_texts = [
            "LangGraph is a library for building stateful, multi-actor applications with LLMs. It extends LangChain to enable cyclic graphs and built-in persistence.",
            "RAG (Retrieval-Augmented Generation) combines retrieval with generation to provide factual, grounded responses.",
            "Self-correcting RAG systems can evaluate document relevance and retry retrieval if documents are not relevant to the query.",
            "ChromaDB is an open-source vector database designed for storing and querying embeddings.",
            "Sentence transformers can generate semantic embeddings for text, enabling similarity search.",
        ]
        vectorstore.add_texts(sample_texts)
        print("Added sample documents to vector store.")
    
    print("Vector store setup complete!\n")


def main():
    """Main function."""
    print("=" * 60)
    print("Self-Correcting RAG Agent with LangGraph")
    print("=" * 60)
    print()
    
    # Setup vector store
    setup_vectorstore()
    
    # Initialize agent
    print("Initializing RAG agent...")
    agent = RAGAgent()
    print("Agent ready!\n")
    
    # Interactive loop
    print("Ask questions (type 'quit' to exit):")
    print("-" * 60)
    
    while True:
        question = input("\nQuestion: ").strip()
        
        if question.lower() in ['quit', 'exit', 'q']:
            print("Goodbye!")
            break
        
        if not question:
            continue
        
        print()
        answer = agent.query(question)
        print("\n" + "=" * 60)
        print("Answer:")
        print("-" * 60)
        print(answer)
        print("=" * 60)


if __name__ == "__main__":
    main()