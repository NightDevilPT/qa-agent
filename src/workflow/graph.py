"""LangGraph wiring for the QA Agent.

Current Pipeline:
START -> ingest_target_node -> clone_workspace_node -> detect_ecosystem_node -> END
"""

from typing import Any, Dict, Type, cast
from langgraph.graph import END, START, StateGraph

from src.services.logger_service import logger
from src.workflow.nodes import (
    build_topological_queue_node,
    classify_files_node,
    clone_workspace_node,
    detect_ecosystem_node,
    ingest_target_node,
)
from src.workflow.state import QAState


# --- Graph Construction ---

def build_graph() -> StateGraph:
    """Construct the LangGraph StateGraph pipeline."""
    builder = StateGraph(cast(Type, QAState))

    # Add nodes
    builder.add_node("ingest_target_node", ingest_target_node)
    builder.add_node("clone_workspace_node", clone_workspace_node)
    builder.add_node("detect_ecosystem_node", detect_ecosystem_node)
    builder.add_node("classify_files_node", classify_files_node)
    builder.add_node("build_topological_queue_node", build_topological_queue_node)

    # Define edges (START -> Node 1 -> Node 2 -> Node 3 -> Node 4 -> Node 5 -> END)
    builder.add_edge(START, "ingest_target_node")
    builder.add_edge("ingest_target_node", "clone_workspace_node")
    builder.add_edge("clone_workspace_node", "detect_ecosystem_node")
    builder.add_edge("detect_ecosystem_node", "classify_files_node")
    builder.add_edge("classify_files_node", "build_topological_queue_node")
    builder.add_edge("build_topological_queue_node", END)

    return builder


def compile_graph():
    """Compile the LangGraph StateGraph pipeline."""
    return build_graph().compile()


def run_qa_agent() -> Dict[str, Any]:
    """Execute the compiled LangGraph QA Agent pipeline.

    Returns:
        Final QAState execution result dictionary.
    """
    logger.info("[Workflow] Compiling LangGraph StateGraph pipeline...")
    app = compile_graph()

    # Initial state payload (dynamically populated by Node 1 and downstream nodes)
    initial_state: Dict[str, Any] = {}

    logger.info("[Workflow] Invoking StateGraph pipeline...")
    final_state = app.invoke(initial_state)
    run_id = final_state.get("run_id", "N/A")
    lang = final_state.get("project_language", "N/A")
    framework = final_state.get("application_framework") or "N/A"
    testable_count = len(final_state.get("testable_files") or [])
    non_testable_count = len(final_state.get("non_testable_files") or [])
    topo_levels = len(final_state.get("topological_levels") or [])
    logger.success(
        f"[Workflow] Pipeline execution finished for run_id '{run_id}' "
        f"(Lang: {lang}, Framework: {framework}, Testable Files: {testable_count}, Non-Testable Files: {non_testable_count}, Parallel Levels: {topo_levels})!"
    )
    return final_state
