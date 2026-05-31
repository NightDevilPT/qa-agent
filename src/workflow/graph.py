"""
Orchestration graph builder for the QA Agent.
Wires nodes and conditional edges together.
"""

from langgraph.graph import StateGraph, START, END
from workflow.state import QAState
from workflow.nodes.clone_files import clone_files
from workflow.nodes.discover_files import discover_files
from workflow.nodes.analyze_project import analyze_project


def build_graph() -> StateGraph:
    """Build the QA Agent state graph."""
    
    graph = StateGraph(QAState)
    
    # --- Register nodes ---
    graph.add_node("clone_files", clone_files)
    graph.add_node("discover_files", discover_files)
    graph.add_node("analyze_project", analyze_project)
    
    # --- Wire edges ---
    # START → clone_files → discover_files → analyze_project → END
    graph.add_edge(START, "clone_files")
    graph.add_edge("clone_files", "discover_files")
    graph.add_edge("discover_files", "analyze_project")
    graph.add_edge("analyze_project", END)
    
    return graph


def compile_graph():
    """Compile and return the graph for invocation."""
    return build_graph().compile()