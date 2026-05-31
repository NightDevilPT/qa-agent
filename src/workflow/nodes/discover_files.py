"""
Discover Files Node — Phase 1: File Discovery

Scans the workspace directory and finds ALL files (source + config + other).
Filters out only:
  - Build artifacts (dist/, build/, coverage/)
  - Dependencies (node_modules/)
  - Existing test files (*.test.*, *.spec.*, __tests__/)

Stores all discovered file paths in state.
"""

from pathlib import Path
from typing import List

from workflow.state import QAState
from utils.logger import get_logger
from constants.languages.config import get_language_config

log = get_logger("discover_files")


def _get_language_extensions(project_language: str) -> tuple:
    """Get file extensions for the selected language."""
    config = get_language_config(project_language)
    return tuple(config.get("extensions", []))


def _get_exclude_patterns(project_language: str) -> List[str]:
    """Get exclude patterns from language config."""
    config = get_language_config(project_language)
    return config.get("exclude_patterns", [])


def _is_excluded(
    relative_path: str,
    exclude_patterns: List[str],
) -> bool:
    """Check if a file should be excluded based on patterns."""
    path_str = relative_path.replace("\\", "/")

    for pattern in exclude_patterns:
        if pattern.startswith("**/"):
            suffix = pattern[3:]
            if path_str.endswith(suffix) or f"/{suffix}" in path_str:
                return True
        if pattern.endswith("/"):
            if path_str.startswith(pattern) or f"/{pattern}" in path_str:
                return True
        if path_str == pattern or path_str.startswith(pattern):
            return True
        if pattern.startswith("*."):
            if path_str.endswith(pattern[1:]):
                return True

    return False


def _is_test_file(relative_path: str) -> bool:
    """Check if file is an existing test file."""
    name = Path(relative_path).name.lower()
    path_str = relative_path.replace("\\", "/")
    return (
        ".test." in name or
        ".spec." in name or
        "__tests__" in path_str
    )


def discover_files(state: QAState) -> dict:
    """
    Scan workspace and find ALL non-excluded, non-test files.
    Stores everything in file_to_be_process.
    """
    log.start("Discover Files Node — Scanning Workspace")

    workspace_root = state.get("workspace_root")
    project_language = state.get("project_language", "typescript")

    if not workspace_root:
        log.error("Missing 'workspace_root' in state")
        return {"file_to_be_process": []}

    workspace_path = Path(workspace_root)
    exclude_patterns = _get_exclude_patterns(project_language)

    log.info("Workspace: %s", workspace_path)
    log.info("Language:  %s", project_language)

    all_files = []
    scanned = 0
    excluded = 0
    skipped_test = 0

    for item in workspace_path.rglob("*"):
        if not item.is_file():
            continue

        scanned += 1
        relative = str(item.relative_to(workspace_path)).replace("\\", "/")

        if _is_excluded(relative, exclude_patterns):
            excluded += 1
            continue

        if _is_test_file(relative):
            skipped_test += 1
            continue

        all_files.append(relative)
        log.info("  [FOUND] %s", relative)

    log.info("Scanned: %d | Found: %d | Excluded: %d | Tests: %d",
             scanned, len(all_files), excluded, skipped_test)

    log.end("Discover files complete — %d files found", len(all_files))

    return {
        "file_to_be_process": all_files,
    }