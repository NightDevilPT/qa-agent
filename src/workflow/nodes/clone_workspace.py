"""Node 2: Workspace Cloning & Sandbox Initialization Node.

Copies target folder or clones Git repository into isolated temporary
workspace directory (.temp/{run_id}) with deterministic run_id hashing and state.json checkpointing.
"""

import hashlib
import shutil
from pathlib import Path
from typing import Any, Dict
import git

from src.services.checkpoint_service import checkpoint_service
from src.services.logger_service import logger
from src.workflow.state import QAState


def clone_workspace_node(state: QAState) -> Dict[str, Any]:
    """Node 2: Create isolated temp workspace and clone/copy target source code.

    Generates deterministic run_id from target_path to enable instant recovery on restart.

    Args:
        state: Active QAState dictionary.

    Returns:
        State update dictionary containing run_id and workspace_dir.
    """
    target_path = state.get("target_path", "")
    input_mode = state.get("input_mode", "FOLDER")

    # 1. Generate deterministic run_id from target_path (e.g. "my_project-8f3a1d")
    if input_mode == "GIT_REPO":
        repo_name = target_path.rstrip("/").split("/")[-1].replace(".git", "")
    else:
        repo_name = Path(target_path).stem or "workspace"

    clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in repo_name)
    target_hash = hashlib.sha256(target_path.strip().encode("utf-8")).hexdigest()[:6]
    run_id = f"{clean_name}-{target_hash}"

    # 2. Prepare workspace directory in .temp/{run_id}
    root_temp_dir = Path(".temp").resolve()
    workspace_dir = root_temp_dir / run_id

    # 3. Check existing checkpoint in .temp/{run_id}/state.json for instant recovery
    existing_checkpoint = checkpoint_service.load_checkpoint(workspace_dir)
    if existing_checkpoint and workspace_dir.exists():
        logger.info(f"[Node 2: CloneWorkspace] Found existing workspace and checkpoint for run_id '{run_id}'. Resuming execution.")
        return {
            "run_id": run_id,
            "workspace_dir": str(workspace_dir)
        }

    workspace_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"[Node 2: CloneWorkspace] Initializing new workspace for run_id '{run_id}' at {workspace_dir}")

    # 4. Clone or copy based on input_mode
    if input_mode == "GIT_REPO":
        logger.info(f"[Node 2: CloneWorkspace] Cloning Git repository '{target_path}'...")
        git.Repo.clone_from(target_path, str(workspace_dir))
        logger.info("[Node 2: CloneWorkspace] Git repository cloned successfully.")

    elif input_mode == "FOLDER":
        source_dir = Path(target_path).resolve()
        logger.info(f"[Node 2: CloneWorkspace] Copying project directory from '{source_dir}'...")

        def ignore_patterns(dir_path: str, names: list[str]) -> set[str]:
            """Ignore build artifacts, venvs, and temp files during copy."""
            ignored = set()
            for name in names:
                if name in (".git", ".temp", ".venv", "venv", "__pycache__", "node_modules", ".idea", ".vscode"):
                    ignored.add(name)
            return ignored

        shutil.copytree(source_dir, workspace_dir, dirs_exist_ok=True, ignore=ignore_patterns)
        logger.info("[Node 2: CloneWorkspace] Project directory copied successfully.")

    res = {
        "run_id": run_id,
        "workspace_dir": str(workspace_dir)
    }

    # Save state snapshot to state.json via CheckpointService
    checkpoint_service.save_checkpoint(workspace_dir, {**state, **res})
    return res
