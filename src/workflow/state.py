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

class CurrentFileStatus(TypedDict):
    """Tracks the active file being processed in the worker loop."""
    current_file: Optional[str]
    current_source_code: Optional[str]
    test_passed: bool
    test_output: Optional[str]
    retries: int
    is_error: bool
    error_log: Optional[str]

# --- Project Analysis & Configuration Types ---
class TestLibConfig(TypedDict, total=False):
    """Holds the execution and setup rules for the chosen test framework."""
    name: str                           # Detected framework name (e.g., "jest", "vitest")
    install_packages: Dict[str, str]    # Packages to install if missing (e.g., {"jest": "^29.0"})
    config_files: Dict[str, str]        # Required config files to write (e.g., jest.config.js content)
    per_file_test_cmd: str              # Command to run a single test (e.g., "npx jest {test_path} --json")

class ProjectAnalysis(TypedDict, total=False):
    """Deep analysis of the workspace environment extracted from package.json and project files."""
    has_package_json: bool              # True for folders/repos with package.json; False for single files
    test_lib: str                       # The detected or default framework name
    test_lib_config: TestLibConfig      # The actual configuration mapping (packages, commands)
    project_dependencies: Dict[str, str]# All external dependencies parsed from package.json
    module_system: Literal["esm", "commonjs", "mixed"] # Determines import vs require syntax

class QAState(TypedDict, total=False):
    """Global LangGraph state. Nodes return only the keys they update."""

    # --- Input (set once at graph start) ---
    target_path: Optional[str] # Used if input_type is "file" or "folder"
    repo_url: Optional[str]    # Used if input_type is "repo"
    input_type: InputType
    project_language: ProjectLanguage  # User-selected: javascript or typescript
    max_retries: int

    # --- Project Analysis & Configuration ---
    project_analysis: ProjectAnalysis    # Populated after checking package.json or applying defaults

    # --- Dependencies & Execution Queue ---
    dependency_graph: DependencyGraph    # Internal file import tree to determine test order
    todo_list: List[str]                 # The priority queue of files to process
    file_to_be_process: List[str]        # Source files to test

    # --- Ledger (completed / failed / skipped) ---
    file_statuses: Dict[str, FileStatus]

    # --- Sandbox runtime (never send ``container_id`` to the LLM) ---
    workspace_root: str  # Host path: mounted QA workspace (src/, tests/, package.json)
    sandbox_ready: bool
    container_id: Optional[str]

    # --- Active Worker State ---
    current_status: CurrentFileStatus
    
    # --- Run completion ---
    final_report: Optional[str]
    total_tokens: int  # Running total of all tokens consumed
    node_tokens: Dict[str, int]  # Tracks tokens used per LangGraph node (e.g., {"plan_strategy": 1500})
