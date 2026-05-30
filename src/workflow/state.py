"""
LangGraph state definitions for the QA Agent.

Paths in lists/dicts are relative to ``target_path`` unless noted otherwise.

Token usage note
----------------
This state is Python orchestration memory passed between graph nodes. It is
**not** automatically sent to the LLM. Only fields you explicitly include in a
node's prompt consume tokens. Large fields (``current_source_code``,
``generated_test_code``, ``test_output``) matter when building prompts; metadata
(``todo_list``, ``dependency_graph``, ``container_id``, ``workspace_root``) cost
nothing unless you dump them into a prompt.
"""

from typing import Dict, List, Literal, Optional, TypedDict
from pydantic import BaseModel, Field

# --- Type aliases ---
InputType = Literal["file", "folder", "repo"]
ProjectLanguage = Literal["javascript", "typescript"]
FileStatusKey = Literal["pending", "in_progress", "completed", "failed", "skipped"]

# importer_path -> list of dependency paths it imports (project-relative)
DependencyGraph = Dict[str, List[str]]

class FileStatus(TypedDict):
    """Immutable ledger entry for one source file (set when work finishes)."""
    status: FileStatusKey
    passed: bool
    retries_used: int
    test_file_path: Optional[str]
    error_log: Optional[str]
    tokens_used: int  # Tokens consumed generating and fixing tests for this specific file

class QAState(TypedDict, total=False):
    """Global LangGraph state. Nodes return only the keys they update."""

    # --- Input (set once at graph start) ---
    target_path: str
    input_type: InputType
    project_language: ProjectLanguage  # User-selected: javascript or typescript
    max_retries: int

    # --- Planning queue (rulebook §3: todo_list drives order) ---
    discovered_files: List[str]  # All valid sources after extract (before LLM filter)
    unplanned_files: List[str]   # Temporary queue for the LLM planning loop
    excluded_files: Dict[str, str]  # path -> reason (types-only, config, etc.)
    dependency_graph: DependencyGraph
    todo_list: List[str]  # Priority-ordered paths to test; shrinks as work completes

    # --- Ledger (completed / failed / skipped) ---
    file_statuses: Dict[str, FileStatus]

    # --- Sandbox runtime (never send ``container_id`` to the LLM) ---
    workspace_root: str  # Host path: mounted QA workspace (src/, tests/, package.json)
    sandbox_ready: bool
    container_id: Optional[str]

    # --- Active file worker context ---
    current_file: Optional[str]
    current_source_code: Optional[str]  # High token cost if included in prompts
    current_language: Optional[str]  # "javascript" | "typescript"
    
    # === CRITICAL FIX ===
    # This was missing! LangGraph was stripping it out of the state dictionary.
    test_file_path: Optional[str]
    # ====================

    # --- Per-file iteration (reset when ``select_next`` picks a new file) ---
    generated_test_code: Optional[str]  # High token cost on retry/fix prompts
    test_passed: bool
    test_output: Optional[str]  # Sandbox stdout/stderr; trim before fix prompts
    retries: int

    # --- Run completion ---
    final_report: Optional[str]
    total_tokens: int  # Running total of all tokens consumed
    node_tokens: Dict[str, int]  # Tracks tokens used per LangGraph node (e.g., {"plan_strategy": 1500})


# --- Structured LLM output for plan_strategy (rulebook §6.1) ---

class PlanStrategyOutput(BaseModel):
    """Parsed planning response. Maps directly into ``QAState`` keys."""
    test_candidates: List[str] = Field(
        description="Project-relative paths worth testing, in any order.",
    )
    excluded_files: Dict[str, str] = Field(
        default_factory=dict,
        description="path -> short reason (e.g. 'types only', 'barrel re-export').",
    )
    dependency_graph: DependencyGraph = Field(
        default_factory=dict,
        description="Each candidate path maps to paths it imports from this repo.",
    )
    todo_list: List[str] = Field(
        description="Same as test_candidates but dependency-sorted (leaves first).",
    )