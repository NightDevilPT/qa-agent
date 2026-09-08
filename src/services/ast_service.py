"""AST & File Classification Service for Autonomous QA Agent.

Provides helper methods for Node 4 file classification by matching
logic_signatures and language_rules from QAState.
"""

from pathlib import Path
from typing import Any, Dict, Tuple
from src.services.logger_service import logger


class ASTService:
    """Service for classifying files as TESTABLE vs NON-TESTABLE."""

    def classify_file(
        self,
        file_path: Path,
        workspace_dir: Path,
        logic_signatures: Dict[str, Any],
        language_rules: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any]]:
        """Classify a file as TESTABLE or NON-TESTABLE using Node 3 rules.

        Args:
            file_path: Path to target source file.
            workspace_dir: Path to project root directory.
            logic_signatures: Control flow keywords, handler signatures, negative signatures.
            language_rules: Extension filters and non-testable filenames.

        Returns:
            Tuple of (is_testable: bool, audit_info: dict).
        """
        try:
            rel_path = str(file_path.relative_to(workspace_dir))
        except ValueError:
            rel_path = str(file_path)

        ext = file_path.suffix.lower()

        # 1. Check non-testable file extensions & filenames
        raw_rules = language_rules.get("non_testable_extensions", [])
        non_testable_set = set()
        for item in raw_rules:
            item_lower = item.lower()
            non_testable_set.add(item_lower)
            clean_ext = item_lower.lstrip("*")
            non_testable_set.add(clean_ext)

        if ext in non_testable_set or file_path.name.lower() in non_testable_set:
            return False, {
                "source_file": rel_path,
                "reason": f"Non-testable file extension or filename ({ext})",
                "skipped_by": "EXTENSION_FILTER",
                "matched_signature_key": "language_rules.non_testable_extensions"
            }

        if not file_path.exists() or not file_path.is_file():
            return False, {
                "source_file": rel_path,
                "reason": "File does not exist or is not a regular file",
                "skipped_by": "FILE_EXISTS_CHECK",
                "matched_signature_key": None
            }

        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore").strip()
        except Exception as e:
            return False, {
                "source_file": rel_path,
                "reason": f"Unreadable file content: {e}",
                "skipped_by": "READ_ERROR",
                "matched_signature_key": None
            }

        if not content:
            return False, {
                "source_file": rel_path,
                "reason": "File is empty (0 bytes)",
                "skipped_by": "EMPTY_FILE_CHECK",
                "matched_signature_key": None
            }

        # 2. Check negative non-testable signatures (e.g. settings =, __all__ =, pass)
        neg_signatures = logic_signatures.get("negative_non_testable_signatures", [])
        for sig in neg_signatures:
            if sig in content:
                return False, {
                    "source_file": rel_path,
                    "reason": f"Matched negative non-testable signature pattern: '{sig}'",
                    "skipped_by": "NEGATIVE_SIGNATURE_CHECK",
                    "matched_signature_key": "negative_non_testable_signatures"
                }

        # Confirmed TESTABLE file!
        return True, {
            "source_file": rel_path,
            "status": "TESTABLE"
        }


# Singleton instance
ast_service = ASTService()
