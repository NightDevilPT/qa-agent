"""
Orchestration graph builder for the QA Agent.
Wires nodes and conditional edges together.
"""

from workflow.nodes.clone_files import clone_files
from langgraph.graph import StateGraph, START, END
from workflow.state import QAState


def build_graph() -> StateGraph:
    """Build the QA Agent state graph."""
    
    graph = StateGraph(QAState)
    
    # --- Register nodes ---
    graph.add_node("clone_files", clone_files)
    
    # --- Wire edges ---
    graph.add_edge(START, "clone_files")
    graph.add_edge("clone_files", END)
    
    return graph


def compile_graph():
    """Compile and return the graph for invocation."""
    return build_graph().compile()