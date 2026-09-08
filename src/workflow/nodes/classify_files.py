"""Node 4: Testable vs Non-Testable File Classifier Node.

Scans workspace directory and classifies files into testable_files vs non-testable_files
using logic_signatures and language_rules from QAState with 0 LLM token consumption.
"""

from pathlib import Path
from typing import Any, Dict, List

from src.services.ast_service import ast_service
from src.services.checkpoint_service import checkpoint_service
from src.services.logger_service import logger
from src.workflow.state import QAState


def classify_files_node(state: QAState) -> Dict[str, Any]:
    """Node 4: Classify project files into testable_files vs non_testable_files.

    Args:
        state: Active QAState dictionary.

    Returns:
        State update dictionary containing testable_files and non_testable_files.
    """
    logger.info("[Node 4: ClassifyFiles] Starting testable vs non-testable file classification...")

    ws_dir_str = state.get("workspace_dir", "")
    workspace_dir = Path(ws_dir_str).resolve() if ws_dir_str else Path(".temp").resolve()

    logic_signatures = state.get("logic_signatures") or {}
    language_rules = state.get("language_rules") or {}

    # Read ignored directories dynamically from Node 3 LLM language_rules
    ignored_dirs = set(language_rules.get("ignored_directories") or [])

    testable_files: List[str] = []
    non_testable_files: List[Dict[str, Any]] = []

    if workspace_dir.exists():
        for file_path in sorted(workspace_dir.rglob("*")):
            if not file_path.is_file():
                continue

            # Skip checkpoint state files
            if file_path.name in ("state.json", "state.json.tmp"):
                continue

            rel_parts = file_path.relative_to(workspace_dir).parts
            matched_ignored_dir = next((part for part in rel_parts[:-1] if part in ignored_dirs), None)

            if matched_ignored_dir:
                non_testable_files.append({
                    "source_file": str(file_path.relative_to(workspace_dir)),
                    "reason": f"File located inside ignored directory ('{matched_ignored_dir}')",
                    "skipped_by": "DIRECTORY_FILTER",
                    "matched_signature_key": "language_rules.ignored_directories"
                })
                continue

            is_testable, audit_info = ast_service.classify_file(
                file_path=file_path,
                workspace_dir=workspace_dir,
                logic_signatures=logic_signatures,
                language_rules=language_rules,
            )

            rel_path = file_path.relative_to(workspace_dir).as_posix()
            if is_testable:
                testable_files.append(rel_path)
            else:
                audit_info["source_file"] = rel_path
                non_testable_files.append(audit_info)

    logger.success(
        f"[Node 4: ClassifyFiles] Classification complete: "
        f"{len(testable_files)} testable files, {len(non_testable_files)} non-testable files."
    )

    update_payload: Dict[str, Any] = {
        "testable_files": testable_files,
        "non_testable_files": non_testable_files,
    }

    # Persist updated state snapshot to state.json via CheckpointService
    full_updated_state = {**state, **update_payload}
    checkpoint_service.save_checkpoint(workspace_dir, full_updated_state)

    logger.table_summary(
        title="File Classification Summary",
        items={
            "Testable Files": len(testable_files),
            "Non-Testable Files": len(non_testable_files),
            "LLM Tokens Consumed": 0,
        }
    )

    return update_payload
