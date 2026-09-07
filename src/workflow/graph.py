"""LangGraph wiring for the QA Agent.

Current Pipeline:
START -> ingest_target_node -> clone_workspace_node -> END
"""

from typing import Any, Dict, Type, cast  # 1. Add Type and cast imports
from langgraph.graph import END, START, StateGraph

from src.services.logger_service import logger
from src.workflow.nodes import clone_workspace_node, ingest_target_node
from src.workflow.state import QAState


# --- Graph Construction ---

def build_graph() -> StateGraph:
    """Construct the LangGraph StateGraph pipeline."""
    # 2. Cast QAState to an unconstrained Type to satisfy StateT upper bound bounds
    builder = StateGraph(cast(Type, QAState))

    builder.add_node("ingest_target_node", ingest_target_node)
    builder.add_node("clone_workspace_node", clone_workspace_node)

    # Entry
    builder.add_edge(START, "ingest_target_node")

    # Transitions
    builder.add_edge("ingest_target_node", "clone_workspace_node")
    builder.add_edge("clone_workspace_node", END)

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
    logger.success(f"[Workflow] Pipeline execution finished for run_id '{final_state.get('run_id')}'!")
    return final_state
