"""
LangGraph wiring for the QA Agent.

Current Pipeline:
START -> clone -> extract -> plan -> build_todo -> init_docker -> 
      -> [generate_test -> run_test -> finalize_file] (Worker Loop) -> END
"""

from langgraph.graph import StateGraph, START, END
from workflow.state import QAState

from workflow.nodes.extract_files import extract_files
from workflow.nodes.clone_repo import clone_repo
from workflow.nodes.plan_strategy import plan_strategy
from workflow.nodes.build_todo_list import build_todo_list
from workflow.nodes.init_docker import init_docker
from workflow.nodes.generate_test import generate_test
from workflow.nodes.run_test import run_test
from workflow.nodes.finalize_file import finalize_file

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
    if state.get("unplanned_files"):
        return "plan_strategy"
    return "build_todo_list"

def route_after_test(state: QAState) -> str:
    """Decides whether to fix a broken test, or finalize the file."""
    passed = state.get("test_passed", False)
    retries = state.get("retries", 0)
    max_retries = state.get("max_retries", 3)
    
    if passed or retries >= max_retries:
        return "finalize_file" # Move on!
        
    return "generate_test" # LOOP BACK to fix the test!

def route_next_file(state: QAState) -> str:
    """Checks if there are more files pending in the queue."""
    if state.get("todo_list"):
        return "generate_test" # LOOP BACK to the next file!
        
    return END # We are completely done!

# --- Graph Construction ---

def build_graph() -> StateGraph:
    builder = StateGraph(QAState)

    builder.add_node("clone_repo", clone_repo)
    builder.add_node("extract_files", extract_files)
    builder.add_node("plan_strategy", plan_strategy)
    builder.add_node("build_todo_list", build_todo_list)
    builder.add_node("init_docker", init_docker)
    builder.add_node("generate_test", generate_test)
    builder.add_node("run_test", run_test)
    builder.add_node("finalize_file", finalize_file)

    # 1. Setup Phase
    builder.add_conditional_edges(START, route_start)
    builder.add_edge("clone_repo", "extract_files")
    builder.add_conditional_edges("extract_files", route_after_extract)
    builder.add_conditional_edges("plan_strategy", route_plan_loop)
    builder.add_edge("build_todo_list", "init_docker")
    
    # 2. Worker Loop Entry
    builder.add_edge("init_docker", "generate_test")
    builder.add_edge("generate_test", "run_test")
    
    # 3. Self-Healing Evaluation (Pass/Fail Router)
    builder.add_conditional_edges("run_test", route_after_test)
    
    # 4. Queue Progression Router
    builder.add_conditional_edges("finalize_file", route_next_file)

    return builder

def compile_graph():
    return build_graph().compile()