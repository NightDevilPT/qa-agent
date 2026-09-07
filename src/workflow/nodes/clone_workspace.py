"""Node 2: Workspace Cloning & Sandbox Initialization Node.

Copies target folder/file or clones Git repository into isolated temporary
workspace directory (.temp/{run_id}).
"""

import shutil
import uuid
from pathlib import Path
from typing import Any, Dict
import git
from src.services.logger_service import logger
from src.workflow.state import QAState


def clone_workspace_node(state: QAState) -> Dict[str, Any]:
    """Node 2: Create isolated temp workspace and clone/copy target source code.

    Args:
        state: Active QAState dictionary.

    Returns:
        State update dictionary containing run_id and workspace_dir.
    """
    target_path = state.get("target_path", "")
    input_mode = state.get("input_mode", "FOLDER")

    # 1. Generate unique run_id (e.g., "my-project-8f3a1d")
    if input_mode == "GIT_REPO":
        repo_name = target_path.rstrip("/").split("/")[-1].replace(".git", "")
    else:
        repo_name = Path(target_path).stem or "workspace"

    clean_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in repo_name)
    short_uuid = uuid.uuid4().hex[:6]
    run_id = f"{clean_name}-{short_uuid}"

    # 2. Prepare workspace directory in .temp/{run_id}
    root_temp_dir = Path(".temp").resolve()
    workspace_dir = root_temp_dir / run_id

    if workspace_dir.exists():
        shutil.rmtree(workspace_dir, ignore_errors=True)

    workspace_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"[Node 2: CloneWorkspace] Initializing workspace for run_id '{run_id}' at {workspace_dir}")

    # 3. Clone or copy based on input_mode
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

    elif input_mode == "SINGLE_FILE":
        source_file = Path(target_path).resolve()
        dest_file = workspace_dir / source_file.name
        shutil.copy2(source_file, dest_file)
        logger.info(f"[Node 2: CloneWorkspace] Copied target file '{source_file.name}' into workspace.")

        # Copy manifest file from parent folder if present
        parent_dir = source_file.parent
        for manifest_name in ("package.json", "pyproject.toml", "go.mod", "Cargo.toml", "requirements.txt"):
            manifest_path = parent_dir / manifest_name
            if manifest_path.exists():
                shutil.copy2(manifest_path, workspace_dir / manifest_name)
                logger.info(f"[Node 2: CloneWorkspace] Copied manifest file '{manifest_name}' into workspace.")

    return {
        "run_id": run_id,
        "workspace_dir": str(workspace_dir)
    }
