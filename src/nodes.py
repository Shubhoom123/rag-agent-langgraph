"""
Node functions for the RAG agent graph.
"""
from typing import Dict, Any
from src.state import GraphState
from src.utils import get_llm, get_vectorstore, format_documents
from config.settings import settings
from langchain_core.documents import Document


# Initialize components
llm = get_llm()
vectorstore = get_vectorstore()


def retrieve(state: GraphState) -> Dict[str, Any]:
    """
    Retrieve relevant documents from vector store.
    """
    print("---RETRIEVING DOCUMENTS---")
    question = state["question"]
    
    # Retrieve documents
    documents = vectorstore.similarity_search(
        question, 
        k=settings.top_k_documents
    )
    
    return {
        "documents": documents,
        "question": question
    }


def generate(state: GraphState) -> Dict[str, Any]:
    """
    Generate answer using retrieved documents.
    """
    print("---GENERATING ANSWER---")
    question = state["question"]
    documents = state["documents"]
    
    # Format context from documents
    context = format_documents(documents)
    
    # Create prompt
    prompt = f"""Answer the question based only on the following context:

Context:
{context}

Question: {question}

Provide a clear and concise answer based on the context above. If the context doesn't contain enough information to answer the question, say so.

Answer:"""
    
    # Generate response
    generation = llm.invoke(prompt)
    
    return {
        "generation": generation,
        "documents": documents,
        "question": question
    }


def grade_documents(state: GraphState) -> Dict[str, Any]:
    """
    Grade the relevance of retrieved documents.
    """
    print("---GRADING DOCUMENTS---")
    question = state["question"]
    documents = state["documents"]
    
    if not documents:
        return {
            "relevance_score": 0.0,
            "web_search_needed": True
        }
    
    # Grade first document
    doc_content = documents[0].page_content
    
    prompt = f"""You are a grader assessing relevance of a retrieved document to a user question.

Retrieved Document:
{doc_content}

User Question: {question}

If the document contains keyword(s) or semantic meaning related to the question, grade it as relevant.

Respond with only 'yes' or 'no' to indicate whether the document is relevant."""
    
    score = llm.invoke(prompt).strip().lower()
    
    # Convert to numeric score
    relevance_score = 1.0 if "yes" in score else 0.0
    
    print(f"Document relevance: {relevance_score}")
    
    return {
        "relevance_score": relevance_score,
        "web_search_needed": relevance_score < settings.relevance_threshold
    }


def web_search_node(state: GraphState) -> Dict[str, Any]:
    """
    Perform web search using DuckDuckGo (FREE - no API key needed).
    """
    print("---WEB SEARCH (DuckDuckGo)---")
    
    question = state["question"]
    retries = state.get("retries", 0) + 1
    
    try:
        from ddgs import DDGS

        # Search the web
        print(f"Searching web for: {question}")
        with DDGS() as ddgs:
            results = list(ddgs.text(question, max_results=3))
        
        # Convert search results to documents
        web_documents = []
        for result in results:
            content = f"{result['title']}\n\n{result['body']}"
            web_documents.append(Document(page_content=content))
        
        if web_documents:
            print(f"Found {len(web_documents)} web results")
            # Add to vector store temporarily for this query
            vectorstore.add_documents(web_documents)
        else:
            print("No web results found")
        
    except Exception as e:
        print(f"Web search error: {e}")
    
    return {
        "retries": retries,
        "web_search_needed": False
    }
