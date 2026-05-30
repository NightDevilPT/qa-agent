"""
Level 2.5: Build Todo List Node
Uses the AI to analyze the dependency graph and sort the todo_list hierarchically.
Tracks token usage for this specific operation.
"""

import json
from typing import List
from pydantic import BaseModel, Field

from workflow.state import QAState
from utils.logger import get_logger
from utils.llm import get_llm

log = get_logger("build_todo_list")

class SortedTodoList(BaseModel):
    todo_list: List[str] = Field(
        description="The sorted array of file paths. Foundational files (no dependencies) must come first."
    )

def build_todo_list(state: QAState) -> dict:
    todo_list = state.get("todo_list") or []
    dependency_graph = state.get("dependency_graph") or {}
    
    # Initialize token counters from state
    total_tokens = state.get("total_tokens") or 0
    node_tokens = (state.get("node_tokens") or {}).copy()

    if not todo_list:
        log.warn("No files in todo_list to sort.")
        return {}

    log.start("Asking AI to hierarchically sort %d files...", len(todo_list))

    prompt = f"""
    You are an expert software architect building a unit testing queue.
    I have an unsorted list of files that need unit tests, and a map of their dependencies.

    Unsorted Files:
    {json.dumps(todo_list, indent=2)}

    Dependency Map (File Path -> Array of files it imports):
    {json.dumps(dependency_graph, indent=2)}

    Your task: Sort the 'Unsorted Files' array strictly from least dependent (leaves) to most dependent (roots).
    A file must appear AFTER the files it imports.
    Return the EXACT same file paths, just reordered. Do not add or remove any files.
    """

    # NEW: include_raw=True lets us get the Pydantic model AND the API usage metadata
    llm = get_llm().with_structured_output(SortedTodoList, include_raw=True)
    
    try:
        response = llm.invoke(prompt)
        
        # Extract parsed data and raw metadata
        result: SortedTodoList = response["parsed"]
        raw_msg = response["raw"]
        
        # Calculate tokens
        used_tokens = 0
        if hasattr(raw_msg, "usage_metadata") and raw_msg.usage_metadata:
            used_tokens = raw_msg.usage_metadata.get("total_tokens", 0)
            
        total_tokens += used_tokens
        node_tokens["build_todo_list"] = node_tokens.get("build_todo_list", 0) + used_tokens
        log.info("Tokens consumed sorting list: %d", used_tokens)

        # Failsafe validation
        original_set = set(todo_list)
        ai_set = set(result.todo_list)
        
        if original_set != ai_set:
            log.warn("AI missed or altered file paths during sorting! Falling back to original unsorted list.")
            return {"todo_list": todo_list, "total_tokens": total_tokens, "node_tokens": node_tokens}

        log.end("AI successfully determined the testing hierarchy.")
        
        return {
            "todo_list": result.todo_list,
            "total_tokens": total_tokens,
            "node_tokens": node_tokens
        }

    except Exception as e:
        log.error("AI sorting failed: %s. Falling back to unsorted list.", e)
        return {"todo_list": todo_list}