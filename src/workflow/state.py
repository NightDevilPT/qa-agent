"""Formal QAState Schema Definition for Autonomous QA Agent.

Defines typed dictionary structures for state persistence across
LangGraph execution nodes.
"""

from typing import Any, Dict, List, Optional, TypedDict


class NonTestableFile(TypedDict, total=False):
    """Schema for skipped non-testable file audit records."""
    source_file: str
    reason: str
    skipped_by: str
    matched_signature_key: Optional[str]


class TestResultFile(TypedDict, total=False):
    """Schema for test execution result records."""
    source_file: str
    test_file: str
    status: str          # "PASSED" | "FAILED" | "POTENTIAL_APPLICATION_BUG"
    failure_category: Optional[str]  # "TOOLING_ERROR" | "BUSINESS_ASSERTION_BUG"
    retries_used: int
    execution_time_ms: int
    tokens_used: int     # Tokens consumed generating and fixing tests for this specific file


class QAState(TypedDict, total=False):
    """State Machine TypedDict Schema for Autonomous QA Agent."""
    run_id: str                              # e.g., "express-8f3a1d"
    target_path: str                         # User input path or URL
    input_mode: str                          # "SINGLE_FILE" | "FOLDER" | "GIT_REPO"
    workspace_dir: str                       # Path to .temp/{name}-{uuid}
    container_id: Optional[str]              # Active Docker container ID
    container_name: Optional[str]            # Named container: qa-agent-{foldername}
    image_name: Optional[str]                # Named image: qa-agent-{foldername}:{manifest_hash}
    manifest_hash: str                       # sha256 checksum of manifest file
    existing_tests_mode: str                 # "ask" | "always" | "never" (Global CLI mode)

    # Universal Ecosystem Profiler Results (Node 3)
    project_language: str                    # "typescript", "python", "go"
    project_type: str                        # "FRONTEND" | "BACKEND_API" | "LIBRARY"
    application_framework: Optional[str]     # "react", "fastapi", "express", "gin"
    manifest_file: Optional[str]             # "package.json", "pyproject.toml", "go.mod"
    import_system: str                       # "COMMONJS" | "ESM" | "PYTHON_RELATIVE" | "PYTHON_ABSOLUTE"
    test_framework: str                      # "jest", "pytest", "testing"
    test_environment: str                    # "jsdom" vs "node" vs "python"
    install_command: str                     # "npm install", "pip install"
    logic_signatures: Dict[str, Any]         # Control flow keywords & AST patterns
    language_rules: Dict[str, Any]           # Extension filters and non-testable filenames

    # State Lists & Queues (Node 4 & Node 5)
    testable_files: List[str]                # Confirmed files requiring test generation
    non_testable_files: List[NonTestableFile]# Skipped files + audit reasons
    existing_tests_map: Dict[str, str]       # Map of source_file -> existing_test_path
    topological_levels: List[List[str]]      # Grouped parallel execution levels
    completed_files: List[TestResultFile]    # Passed test files
    failed_files: List[TestResultFile]       # Failed test files or application bugs

    # Execution Worker & Guardrails
    current_file_batch: List[str]            # Active parallel file batch for current level
    current_retries: int                     # Retries spent on current file batch
    total_tokens_used: int                   # Cumulative tokens consumed across run
    node_tokens: Dict[str, int]              # Tracks tokens used per LangGraph node (e.g., {"detect_ecosystem_node": 75})
    max_token_budget: int                    # Maximum token budget cap (default 50,000)
    per_test_timeout_sec: int                # Docker test execution timeout (default 30s)
