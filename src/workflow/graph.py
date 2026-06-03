"""
Orchestration graph builder for the QA Agent.
Wires nodes and conditional edges together.
"""

from langgraph.graph import StateGraph, START, END
from workflow.state import QAState

# --- Node Imports ---
from workflow.nodes.clone_files import clone_files
from workflow.nodes.discover_files import discover_files
from workflow.nodes.analyze_project import analyze_project
from workflow.nodes.plan_strategy import plan_strategy
from workflow.nodes.setup_sandbox import setup_sandbox

# --- Phase 5: Worker Loop Nodes ---
from workflow.nodes.select_next_file import select_next_file
from workflow.nodes.generate_test import generate_test
from workflow.nodes.execute_test import execute_test

# --- Phase 6: Finalization Nodes ---
from workflow.nodes.generate_report import generate_report
from workflow.nodes.teardown import teardown


# ================================================================
# Conditional Routers
# ================================================================

def route_after_select(state: QAState) -> str:
    """
    Router R1: If there are no files left to test, exit the loop 
    and generate the report. Otherwise, move to generate a test.
    """
    current_file = state.get("current_status", {}).get("current_file")
    
    if current_file is None:
        return "generate_report"  # Queue is empty, move to finalization
        
    return "generate_test"


def route_after_execute(state: QAState) -> str:
    """
    Router R2: Decides if we move to the next file or retry generating 
    the current one based on test results and retry limits.
    """
    current_status = state.get("current_status", {})
    max_retries = state.get("max_retries", 3)
    
    passed = current_status.get("test_passed", False)
    retries = current_status.get("retries", 0)
    
    if passed:
        return "select_next_file"  # Success! Pick the next file.
        
    if retries < max_retries:
        return "generate_test"     # Failed, but we have retries left. Heal the code.
        
    return "select_next_file"      # Failed permanently. Pick the next file.


# ================================================================
# Graph Builder
# ================================================================

def build_graph() -> StateGraph:
    """Build the QA Agent state graph."""
    
    graph = StateGraph(QAState)
    
    # --- Register nodes ---
    graph.add_node("clone_files", clone_files)
    graph.add_node("discover_files", discover_files)
    graph.add_node("analyze_project", analyze_project)
    graph.add_node("plan_strategy", plan_strategy)
    graph.add_node("setup_sandbox", setup_sandbox)
    
    # Worker Loop Nodes
    graph.add_node("select_next_file", select_next_file)
    graph.add_node("generate_test", generate_test)
    graph.add_node("execute_test", execute_test)
    
    # Finalization Nodes
    graph.add_node("generate_report", generate_report)
    graph.add_node("teardown", teardown)
    
    # --- Wire linear edges ---
    graph.add_edge(START, "clone_files")
    graph.add_edge("clone_files", "discover_files")
    graph.add_edge("discover_files", "analyze_project")
    graph.add_edge("analyze_project", "plan_strategy")
    graph.add_edge("plan_strategy", "setup_sandbox")
    
    # Connect preparation phase to the worker loop
    graph.add_edge("setup_sandbox", "select_next_file")
    
    # --- Wire conditional worker loop ---
    
    # 1. After selecting, either generate or generate report
    graph.add_conditional_edges(
        "select_next_file", 
        route_after_select
    )
    
    # 2. Generation always leads directly to execution
    graph.add_edge("generate_test", "execute_test")
    
    # 3. After execution, either loop back to generate (retry) or grab next file
    graph.add_conditional_edges(
        "execute_test", 
        route_after_execute
    )
    
    # --- Wire finalization edges ---
    graph.add_edge("generate_report", "teardown")
    graph.add_edge("teardown", END)
    
    return graph


def compile_graph():
    """Compile and return the graph for invocation."""
    return build_graph().compile()