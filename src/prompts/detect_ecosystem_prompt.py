"""Ecosystem Detection LLM Prompt Templates.

Defines professional system prompts and user prompt builders for Node 3 ecosystem profiling
supporting FOLDER and GIT_REPO project modes.
"""

from typing import List, Optional

SYSTEM_ECOSYSTEM_PROMPT = (
    "You are a Senior System Architect profiling a software repository ecosystem. "
    "Given the project input mode, root workspace file listing, and text content snippets, "
    "analyze the codebase and return the structured EcosystemProfileSchema containing "
    "primary programming language, project type, framework, import system, test framework, "
    "execution environment, dependency install command, logic AST signatures, and language rules.\n\n"
    "CRITICAL RULES FOR LANGUAGE RULES:\n"
    "1. 'non_testable_extensions': MUST list ONLY non-code asset, config, styling, documentation, and build artifact extensions "
    "or patterns to exclude from unit testing (e.g. '.png', '.jpg', '.svg', '.css', '.scss', '.json', '.md', '.env', '.d.ts', '.lock', '.map').\n"
    "2. NEVER include main programming language source code extensions (such as '.js', '.jsx', '.ts', '.tsx', '.py', '.go', '.rs', '.java') in 'non_testable_extensions' "
    "because source code files are the primary target files to be tested!\n"
    "3. 'ignored_directories': MUST list build output, dependency cache, virtual environment, VCS, and IDE directories specific to this language and framework "
    "(e.g., 'node_modules', 'dist', 'build', '.next', '__pycache__', '.venv', 'venv', 'target', 'vendor', 'coverage', '.git', '.idea', '.vscode').\n"
    "4. 'import_export_patterns': MUST list valid Python-compatible regex strings with capture group 1 capturing imported module/file paths "
    "for this programming language (e.g., for JS/TS: '(?:import|export|require)\\\\s*(?:\\\\([^)]*\\\\)|[^{}]*|\\\\{[^}]*\\\\})?\\\\s*(?:from\\\\s*)?[\'\"]([^\'\"]+)[\'\"]'; "
    "for Python: '^\\\\s*(?:from|import)\\\\s+([\\\\.\\\\w]+)'; for Go: 'import\\\\s*(?:\\\\(\\\\s*)?[\'\"]([^\'\"]+)[\'\"]')."
)


def build_detect_ecosystem_user_prompt(
    input_mode: str,
    root_files: List[str],
    manifest_snippet: str,
) -> str:
    """Build compact user prompt for Node 3 ecosystem profiling.

    Args:
        input_mode: Project input mode ("FOLDER" or "GIT_REPO").
        root_files: List of top-level directory/file names in workspace.
        manifest_snippet: Truncated content snippet of top workspace files.

    Returns:
        Formatted user prompt string.
    """
    return (
        f"Input Mode: {input_mode}\n"
        f"Root Workspace Files: {root_files[:20]}\n"
        f"Root Workspace Content Snippet:\n{manifest_snippet[:600]}\n\n"
        f"Profile this repository ecosystem accurately."
    )
