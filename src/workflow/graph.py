"""
LangGraph wiring for the QA Agent.

Current Pipeline:
START -> clone_repo -> extract_files -> plan_strategy (loop) -> build_todo_list -> init_docker -> END
"""

from workflow.state import QAState
from langgraph.graph import StateGraph, START, END

from workflow.nodes.clone_repo import clone_repo
from workflow.nodes.extract_files import extract_files
from workflow.nodes.plan_strategy import plan_strategy
from workflow.nodes.build_todo_list import build_todo_list

# --- Conditional Routers ---

def route_start(state: QAState) -> str:
    target = state.get("target_path", "")
    if target.startswith(("http://", "https://", "git@")):
        return "clone_repo"
    return "extract_files"

def route_after_extract(state: QAState) -> str:
    if not state.get("unplanned_files"):
        return END
    return "plan_strategy"

def route_plan_loop(state: QAState) -> str:
    """If there are still files to plan, loop back. Otherwise, move to sorting."""
    if state.get("unplanned_files"):
        return "plan_strategy" # LOOP BACK
    
    # When empty, the loop is done. Send it to the AI for sorting!
    return "build_todo_list"

# --- Graph Construction ---

def build_graph() -> StateGraph:
    builder = StateGraph(QAState)

    builder.add_node("clone_repo", clone_repo)
    builder.add_node("extract_files", extract_files)
    builder.add_node("plan_strategy", plan_strategy)
    builder.add_node("build_todo_list", build_todo_list)

    # Entry
    builder.add_conditional_edges(START, route_start)

    # Transitions
    builder.add_edge("clone_repo", "extract_files")
    
    builder.add_conditional_edges("extract_files", route_after_extract)
    
    # The Planning Loop -> goes to build_todo_list when done
    builder.add_conditional_edges("plan_strategy", route_plan_loop)

    # After sorting, initialize the Docker sandbox!
    builder.add_edge("build_todo_list", END)

    return builder

def compile_graph():
    return build_graph().compile()