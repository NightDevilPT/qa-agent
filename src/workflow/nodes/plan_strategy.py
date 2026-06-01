"""
Plan Strategy Node — Phase 3: Planning

Executes the exact 3-step flow:
  1. Pass all files to AI to filter which files need test cases.
  2. Loop through that list, read content for each, and ask AI if it requires a test and what its dependencies are.
  3. Perform topological sorting to identify the correct test order.
  
Tracks token usage per-file and at the batch level.
"""

import graphlib
from pathlib import Path
from typing import List, Dict, Optional, Any

from pydantic import BaseModel, Field
from langchain_core.messages import AIMessage

from workflow.state import QAState, FileStatus
from utils.logger import get_logger
from utils.llm import get_llm

log = get_logger("plan_strategy")


# ================================================================
# Pydantic Models for Structured Output
# ================================================================

class Step1CandidateFiles(BaseModel):
    """Output for Step 1: Initial file filtering"""
    candidate_files: List[str] = Field(
        description="List of file paths that likely need test cases based on their names."
    )

class Step2FileAnalysis(BaseModel):
    """Output for Step 2: Individual file analysis"""
    needs_test: bool = Field(
        description="True if this file actually requires test cases, False otherwise."
    )
    dependencies: List[str] = Field(
        default_factory=list,
        description="List of OTHER internal file paths this file imports/uses."
    )


# ================================================================
# Utilities
# ================================================================

def _extract_token_usage(response: AIMessage) -> int:
    """Extract total token usage safely from raw AIMessage metadata."""
    try:
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata.get("total_tokens", 0)
        if hasattr(response, "response_metadata") and response.response_metadata:
            return response.response_metadata.get("token_usage", {}).get("total_tokens", 0)
    except Exception:
        pass
    return 0

def _read_file_head(workspace_root: str, file_path: str, max_chars: int = 2000) -> Optional[str]:
    """Reads the file content (truncated to protect the LLM context window)."""
    full_path = Path(workspace_root) / file_path
    try:
        if full_path.is_file():
            content = full_path.read_text(encoding="utf-8", errors="replace")
            return content[:max_chars] + "\n...[TRUNCATED]" if len(content) > max_chars else content
    except Exception as e:
        log.warning("Could not read %s: %s", file_path, e)
        return None

def _sort_by_dependencies(todo_list: List[str], dependency_graph: Dict[str, List[str]]) -> List[str]:
    """Step 3: Topologically sorts the files so zero-dependency files are tested first."""
    safe_graph = {file: [] for file in todo_list}
    
    for file, imports in dependency_graph.items():
        if file in safe_graph:
            # Only keep dependencies that are actually in our confirmed todo list
            safe_graph[file] = [imp for imp in imports if imp in todo_list]

    try:
        sorter = graphlib.TopologicalSorter(safe_graph)
        return list(sorter.static_order())
    except graphlib.CycleError as e:
        log.warning("Circular dependency detected. Falling back to unsorted list.")
        return todo_list


# ================================================================
# Main Node Entrypoint
# ================================================================

def plan_strategy(state: QAState) -> dict:
    log.start("Plan Strategy Node — Phase 3: Planning")

    workspace_root = state.get("workspace_root")
    file_list = state.get("file_to_be_process", [])
    total_tokens = state.get("total_tokens", 0)
    node_tokens = state.get("node_tokens", {})

    if not workspace_root or not file_list:
        log.warning("Missing workspace data or files to process.")
        return {"todo_list": [], "dependency_graph": {}, "file_statuses": {}}

    llm = get_llm(temperature=0.0)
    node_token_count = 0
    
    # Dictionary to track our precise per-file token usage
    file_token_breakdown: Dict[str, int] = {}

    # ----------------------------------------------------------------
    # STEP 1: Pass file paths to AI to get candidates
    # ----------------------------------------------------------------
    log.section("Step 1: AI Path Filtering")
    
    prompt_1 = f"""Role: QA Architect.
Task: Review the following list of file paths. Identify which files likely contain application logic that requires unit testing.
Exclude configuration files, pure interfaces, and simple barrel exports (e.g., index.js).

Files to evaluate:
{chr(10).join(f"- {f}" for f in file_list)}"""

    step1_llm = llm.with_structured_output(Step1CandidateFiles, include_raw=True)
    step1_response = step1_llm.invoke(prompt_1)
    
    candidates = step1_response["parsed"].candidate_files
    step1_tokens = _extract_token_usage(step1_response["raw"])
    
    # Record Step 1 tokens
    node_token_count += step1_tokens
    file_token_breakdown["file_to_be_process"] = step1_tokens
    
    log.info("Step 1 returned %d candidate files.", len(candidates))

    if not candidates:
        return {"todo_list": [], "dependency_graph": {}, "file_statuses": {}}

    # ----------------------------------------------------------------
    # STEP 2: Loop through candidates, get content, and ask AI
    # ----------------------------------------------------------------
    log.section("Step 2: Loop & AI Content Analysis")
    
    todo_list = []
    dependency_graph = {}
    
    step2_llm = llm.with_structured_output(Step2FileAnalysis, include_raw=True)

    for file_path in candidates:
        content = _read_file_head(workspace_root, file_path)
        if not content:
            continue
            
        prompt_2 = f"""Role: QA Architect.
Task: Analyze the content of the following file to determine if it requires unit tests, and map its internal dependencies.

File Path: {file_path}
Content (Truncated):
{content}

Extraction Rules:
1. needs_test: Set to True if the file contains executable logic, classes, or functions. Set to False if it is only constants, types, or basic exports.
2. dependencies: List the exact paths of OTHER internal files imported within this file. Ignore external libraries (like React or Express)."""

        try:
            response = step2_llm.invoke(prompt_2)
            parsed: Step2FileAnalysis = response["parsed"]
            file_tokens = _extract_token_usage(response["raw"])
            
            # Record Step 2 tokens for this specific file
            node_token_count += file_tokens
            file_token_breakdown[file_path] = file_tokens
            
            # Process AI decision
            if parsed.needs_test:
                todo_list.append(file_path)
                dependency_graph[file_path] = parsed.dependencies
                log.info("[ADDED] %s (Dependencies: %d)", file_path, len(parsed.dependencies))
            else:
                log.info("[SKIPPED] %s", file_path)
                
        except Exception as e:
            log.error("AI Analysis failed for %s: %s", file_path, e)

    # ----------------------------------------------------------------
    # STEP 3: Topological Sorting & Ledger Setup
    # ----------------------------------------------------------------
    log.section("Step 3: Topological Sorting")
    
    sorted_todo_list = _sort_by_dependencies(todo_list, dependency_graph)
    
    file_statuses: Dict[str, FileStatus] = {}
    for f in sorted_todo_list:
        file_statuses[f] = {
            "status": "pending", 
            "passed": False, 
            "retries_used": 0,
            "test_file_path": None, 
            "error_log": None, 
            "tokens_used": 0
        }

    log.info("Final Sorted Todo List: %d files", len(sorted_todo_list))
    log.info("Node tokens used: %d", node_token_count)
    log.end("Plan strategy complete")

    return {
        "todo_list": sorted_todo_list,
        "dependency_graph": dependency_graph,
        "file_statuses": file_statuses,
        "total_tokens": total_tokens + node_token_count,
        "node_tokens": {
            **node_tokens,
            "plan_strategy": node_token_count,
            "plan_strategy_files": file_token_breakdown # Injecting your specific JSON breakdown here
        },
    }