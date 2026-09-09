"""Formal QAState Schema Definition for Autonomous QA Agent.

Defines typed dictionary structures for state persistence across
LangGraph execution nodes.
"""

from typing import Dict, List, Optional, TypedDict


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


class LogicSignaturesDict(TypedDict, total=False):
    """Schema for logic AST signatures detected by ecosystem profiler (Node 3)."""
    control_flow_keywords: List[str]
    async_and_event_signatures: List[str]
    framework_handler_signatures: List[str]
    database_query_signatures: List[str]
    negative_non_testable_signatures: List[str]


class LanguageRulesDict(TypedDict, total=False):
    """Schema for language rules and import/export patterns detected by ecosystem profiler (Node 3)."""
    non_testable_extensions: List[str]
    ignored_directories: List[str]
    import_export_patterns: List[str]


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
    logic_signatures: LogicSignaturesDict    # Control flow keywords & AST patterns
    language_rules: LanguageRulesDict        # Extension filters, ignored dirs & import regexes

    # State Lists & Queues (Node 4 & Node 5)
    testable_files: List[str]                # Confirmed files requiring test generation
    non_testable_files: List[NonTestableFile]# Skipped files + audit reasons
    existing_tests_map: Dict[str, str]       # Map of source_file -> existing_test_path
    topological_levels: List[str]            # Flat array of string file paths in topological order
    completed_files: List[TestResultFile]    # Passed test files
    failed_files: List[TestResultFile]       # Failed test files or application bugs

    # Execution Worker & Guardrails
    current_file: Optional[str]              # Active single file currently being processed
    current_file_batch: Optional[List[str]]  # Optional legacy batch compatibility
    should_skip_test: bool                   # Node 8 skip flag if existing test preserved
    user_confirmed: bool                     # User interactive confirmation flag
    generated_test_code: Optional[str]       # Node 9 generated test code string
    test_file_path: Optional[str]            # Saved test file relative path
    current_retries: int                     # Retries spent on current active file
    total_tokens_used: int                   # Cumulative tokens consumed across run
    node_tokens: Dict[str, int]              # Tracks tokens used per LangGraph node
    max_token_budget: int                    # Maximum token budget cap (default 50,000)
    per_test_timeout_sec: int                # Docker test execution timeout (default 30s)
    last_exit_code: Optional[int]            # Last test execution exit code (0 = PASS)
    raw_logs: Optional[str]                  # Raw stdout/stderr test execution log
    summary_report: Optional[str]            # Final Markdown execution summary report







