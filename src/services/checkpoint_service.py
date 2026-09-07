"""Checkpoint Service for Autonomous QA Agent.

Provides state snapshot saving, loading, and recovery for crash persistence
and instant --resume capabilities via state.json.
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, Optional
from src.services.logger_service import logger


class CheckpointService:
    """Service for persisting and restoring state snapshots to/from state.json."""

    CHECKPOINT_FILENAME = "state.json"

    def get_checkpoint_path(self, workspace_dir: str | Path) -> Path:
        """Get absolute path to state.json in workspace directory."""
        return Path(workspace_dir) / self.CHECKPOINT_FILENAME

    def save_checkpoint(self, workspace_dir: str | Path, state: Dict[str, Any]) -> Path:
        """Save QAState snapshot dictionary to state.json safely.

        Args:
            workspace_dir: Path to project workspace directory.
            state: Active QAState dictionary.

        Returns:
            Path to saved checkpoint file.
        """
        checkpoint_path = self.get_checkpoint_path(workspace_dir)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)

        serializable_state = json.loads(json.dumps(state, default=str))

        tmp_path = checkpoint_path.with_suffix(".json.tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(serializable_state, f, indent=2)

        os.replace(tmp_path, checkpoint_path)
        logger.debug(f"[CheckpointService] State checkpoint saved: {checkpoint_path}")
        return checkpoint_path

    def load_checkpoint(self, workspace_dir: str | Path) -> Optional[Dict[str, Any]]:
        """Load state snapshot from state.json if present.

        Args:
            workspace_dir: Path to project workspace directory.

        Returns:
            Loaded QAState dictionary or None if checkpoint does not exist.
        """
        checkpoint_path = self.get_checkpoint_path(workspace_dir)
        if not checkpoint_path.exists():
            logger.debug(f"[CheckpointService] No checkpoint file found at {checkpoint_path}")
            return None

        try:
            with open(checkpoint_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            logger.info(f"[CheckpointService] Successfully loaded checkpoint from {checkpoint_path}")
            return state
        except Exception as e:
            logger.error(f"[CheckpointService] Failed to read checkpoint {checkpoint_path}: {e}")
            return None

    def has_checkpoint(self, workspace_dir: str | Path) -> bool:
        """Check if state.json exists in workspace directory."""
        return self.get_checkpoint_path(workspace_dir).exists()

    def clear_checkpoint(self, workspace_dir: str | Path) -> None:
        """Remove state.json checkpoint file if present."""
        checkpoint_path = self.get_checkpoint_path(workspace_dir)
        if checkpoint_path.exists():
            checkpoint_path.unlink()
            logger.info(f"[CheckpointService] Cleared checkpoint: {checkpoint_path}")


# Singleton instance
checkpoint_service = CheckpointService()
