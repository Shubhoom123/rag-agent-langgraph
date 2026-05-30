"""
Main RAG agent implementation using LangGraph.
"""
from langgraph.graph import StateGraph, END
from src.state import GraphState
from src.nodes import (
    retrieve,
    generate,
    grade_documents,
    web_search_node
)
from config.settings import settings


def decide_to_generate(state: GraphState) -> str:
    """
    Determine whether to generate an answer or retry with web search.
    
    Args:
        state: Current graph state
        
    Returns:
        Next node to execute
    """
    web_search_needed = state.get("web_search_needed", False)
    retries = state.get("retries", 0)
    
    if not web_search_needed:
        # Documents are relevant, proceed to generation
        return "generate"
    else:
        # Documents not relevant
        if retries < settings.max_retries:
            # Try web search
            return "web_search"
        else:
            # Max retries reached, generate anyway
            print("Max retries reached. Generating with available documents.")
            return "generate"


def build_agent() -> StateGraph:
    """
    Build and compile the RAG agent graph.
    
    Returns:
        Compiled StateGraph
    """
    # Create graph
    workflow = StateGraph(GraphState)
    
    # Add nodes
    workflow.add_node("retrieve", retrieve)
    workflow.add_node("grade_documents", grade_documents)
    workflow.add_node("generate", generate)
    workflow.add_node("web_search", web_search_node)
    
    # Build graph flow
    workflow.set_entry_point("retrieve")
    
    # After retrieval, grade documents
    workflow.add_edge("retrieve", "grade_documents")
    
    # Conditional edge: decide whether to generate or retry
    workflow.add_conditional_edges(
        "grade_documents",
        decide_to_generate,
        {
            "generate": "generate",
            "web_search": "web_search"
        }
    )
    
    # After web search, retrieve again
    workflow.add_edge("web_search", "retrieve")
    
    # After generation, end
    workflow.add_edge("generate", END)
    
    # Compile the graph
    app = workflow.compile()
    
    return app


class RAGAgent:
    """RAG Agent wrapper class."""
    
    def __init__(self):
        """Initialize the RAG agent."""
        self.app = build_agent()
    
    def query(self, question: str) -> str:
        """
        Query the RAG agent.
        
        Args:
            question: User question
            
        Returns:
            Generated answer
        """
        # Initialize state
        initial_state = {
            "question": question,
            "generation": None,
            "documents": [],
            "relevance_score": 0.0,
            "retries": 0,
            "web_search_needed": False
        }
        
        # Run the graph
        result = self.app.invoke(initial_state)
        
        return result.get("generation", "Unable to generate an answer.")