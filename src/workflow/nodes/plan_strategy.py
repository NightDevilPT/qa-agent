"""
Level 2: Intelligent Planning Node
Analyzes a single file to check testability and dependencies, updating the queue.
Tracks token usage per file analyzed.
"""

from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

from workflow.state import QAState
from utils.logger import get_logger
from utils.llm import get_llm

log = get_logger("plan_strategy")

class FileAnalysis(BaseModel):
    needs_tests: bool = Field(description="True if the file contains testable logic. False if it is only types, interfaces, simple exports, or config.")
    exclusion_reason: str = Field(description="If needs_tests is False, state the reason. Empty if True.")
    dependencies: List[str] = Field(description="List of other local project files this file imports.")

def plan_strategy(state: QAState) -> dict:
    """
    Pops one file from the queue, analyzes it via LLM, and updates lists.
    """
    unplanned = state.get("unplanned_files") or []
    
    if not unplanned:
        return {} # Failsafe: queue is empty

    # 1. Pop the first file from the queue
    current_file = unplanned[0]
    remaining_unplanned = unplanned[1:]
    
    target_path = Path(state.get("target_path", ""))
    full_path = target_path / current_file
    
    log.start("Analyzing file: %s (%d remaining)", current_file, len(remaining_unplanned))
    
    # 2. Get existing state lists
    todo_list = (state.get("todo_list") or []).copy()
    excluded_files = (state.get("excluded_files") or {}).copy()
    dependency_graph = (state.get("dependency_graph") or {}).copy()
    
    # Initialize token counters from state
    total_tokens = state.get("total_tokens") or 0
    node_tokens = (state.get("node_tokens") or {}).copy()

    try:
        content = full_path.read_text(encoding="utf-8")
        if len(content) > 15000:
            content = content[:15000] + "\n...[TRUNCATED]"
            
        prompt = (
            f"Analyze the following file located at '{current_file}':\n\n"
            f"```\n{content}\n```\n\n"
            "Determine if this file needs unit tests. Also, list any internal "
            "project dependencies it imports."
        )
        
        # NEW: include_raw=True lets us get the parsed model AND the token metadata
        llm = get_llm().with_structured_output(FileAnalysis, include_raw=True)
        response = llm.invoke(prompt)
        
        # Extract parsed data and raw metadata
        analysis: FileAnalysis = response["parsed"]
        raw_msg = response["raw"]
        
        # Calculate tokens used for this specific API call
        used_tokens = 0
        if hasattr(raw_msg, "usage_metadata") and raw_msg.usage_metadata:
            used_tokens = raw_msg.usage_metadata.get("total_tokens", 0)
            
        # Update running totals
        total_tokens += used_tokens
        node_tokens["plan_strategy"] = node_tokens.get("plan_strategy", 0) + used_tokens
        
        if analysis.needs_tests:
            todo_list.append(current_file)
            dependency_graph[current_file] = analysis.dependencies
            log.info("Result: Added to todo (Dependencies: %d) [Tokens: %d]", len(analysis.dependencies), used_tokens)
        else:
            excluded_files[current_file] = analysis.exclusion_reason
            log.info("Result: Excluded (Reason: %s) [Tokens: %d]", analysis.exclusion_reason, used_tokens)
            
    except Exception as e:
        log.error("Failed to analyze %s: %s", current_file, e)
        excluded_files[current_file] = f"Analysis error: {e}"

    # 3. Return the updated state
    return {
        "unplanned_files": remaining_unplanned,
        "todo_list": todo_list,
        "excluded_files": excluded_files,
        "dependency_graph": dependency_graph,
        "total_tokens": total_tokens,
        "node_tokens": node_tokens
    }