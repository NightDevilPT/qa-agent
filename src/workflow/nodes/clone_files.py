"""
Clone Files Node — Phase 1: Ingestion & Extraction

Handles all three input types:
  - file   → validates and copies single file into workspace
  - folder → validates and copies entire folder into workspace
  - repo   → clones git repository into workspace

Creates workspace at: <project_root>/.temp/qa-agent-{uuid}/
"""

import shutil
import uuid
import subprocess
from pathlib import Path
from typing import Optional

from workflow.state import QAState
from utils.logger import get_logger

log = get_logger("clone_files")


def _validate_file(path: Path) -> bool:
    """Check if path exists and is a file."""
    return path.exists() and path.is_file()


def _validate_folder(path: Path) -> bool:
    """Check if path exists and is a directory."""
    return path.exists() and path.is_dir()


def _validate_repo_url(url: str) -> bool:
    """Basic check that URL looks like a git repository."""
    return bool(url) and (
        url.startswith("http") or 
        url.startswith("git@") or 
        url.endswith(".git")
    )


def _generate_workspace_id() -> str:
    """Generate a unique workspace identifier."""
    return str(uuid.uuid4())[:8]


def _get_project_root() -> Path:
    """Get the project root directory (where .temp will be created)."""
    # Go up from src/workflow/nodes/ to project root
    return Path(__file__).resolve().parent.parent.parent.parent


def _get_workspace_base(project_root: Path, workspace_id: str) -> Path:
    """Get the base path for a workspace (does NOT create it)."""
    return project_root / ".temp" / f"qa-agent-{workspace_id}"


def _handle_file(target_path: str, workspace_base: Path) -> Optional[str]:
    """
    Validate and copy a single file into workspace/src/.
    Returns the workspace path, or None on failure.
    """
    source = Path(target_path).resolve()
    
    if not _validate_file(source):
        log.error("Invalid file path: %s", target_path)
        return None
    
    # Create workspace directories
    workspace_path = workspace_base / "workspace"
    src_dir = workspace_path / "src"
    tests_dir = workspace_path / "tests"
    src_dir.mkdir(parents=True, exist_ok=True)
    tests_dir.mkdir(parents=True, exist_ok=True)
    
    # Copy file into workspace/src/
    destination = src_dir / source.name
    shutil.copy2(source, destination)
    
    log.info("Copied file: %s → %s", source.name, destination)
    return str(workspace_path)


def _handle_folder(target_path: str, workspace_base: Path) -> Optional[str]:
    """
    Validate and copy entire folder into workspace/.
    Preserves directory structure and safely merges with required folders.
    Returns the workspace path, or None on failure.
    """
    source = Path(target_path).resolve()
    
    if not _validate_folder(source):
        log.error("Invalid folder path: %s", target_path)
        return None
    
    workspace_path = workspace_base / "workspace"
    
    try:
        # Use copytree to copy everything at once.
        # Ignore massive/unnecessary folders to prevent crashes and save time.
        shutil.copytree(
            source, 
            workspace_path, 
            ignore=shutil.ignore_patterns("node_modules", ".git", ".next", "dist", "build"),
            dirs_exist_ok=True
        )
        
        # Ensure our required directories exist in the workspace, 
        # even if they weren't in the source folder.
        (workspace_path / "src").mkdir(parents=True, exist_ok=True)
        (workspace_path / "tests").mkdir(parents=True, exist_ok=True)
        
        log.info("Copied folder: %s → %s", source.name, workspace_path)
        return str(workspace_path)
        
    except Exception as e:
        log.error("Failed to copy folder %s: %s", target_path, e)
        return None


def _handle_repo(repo_url: str, workspace_base: Path) -> Optional[str]:
    """
    Clone a git repository into workspace/.
    Let git create the workspace directory (must be non-existent or empty).
    Returns the workspace path, or None on failure.
    """
    if not _validate_repo_url(repo_url):
        log.error("Invalid repository URL: %s", repo_url)
        return None
    
    # The workspace directory must NOT exist — git clone will create it
    workspace_path = workspace_base / "workspace"
    
    # If workspace already exists from a previous failed run, remove it
    if workspace_path.exists():
        log.warn("Removing existing workspace: %s", workspace_path)
        shutil.rmtree(workspace_path, ignore_errors=True)
    
    try:
        # Create parent directory (.temp/qa-agent-{id}/) but NOT workspace/
        workspace_base.mkdir(parents=True, exist_ok=True)
        
        # Git clone creates the workspace/ directory itself
        log.info("Cloning %s ...", repo_url)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(workspace_path)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        
        if result.returncode != 0:
            log.error("Git clone failed: %s", result.stderr.strip())
            return None
        
        log.info("Repository cloned successfully")
        
        # After clone, ensure tests/ directory exists
        tests_dir = workspace_path / "tests"
        tests_dir.mkdir(exist_ok=True)
        
        # If no src/ directory, create one (some repos have flat structure)
        src_dir = workspace_path / "src"
        if not src_dir.exists():
            src_dir.mkdir(exist_ok=True)
        
        return str(workspace_path)
        
    except subprocess.TimeoutExpired:
        log.error("Git clone timed out after 120s: %s", repo_url)
        return None
    except FileNotFoundError:
        log.error("Git is not installed or not in PATH")
        return None
    except Exception as e:
        log.error("Unexpected error during clone: %s", e)
        return None


def clone_files(state: QAState) -> dict:
    """
    Main node function.
    
    Reads input_type and target_path (or repo_url) from state.
    Creates workspace, copies/clones project, validates result.
    
    Returns updated state with workspace_root set.
    """
    log.start("Clone Files Node — Phase 1: Ingestion")
    
    input_type = state.get("input_type")
    target_path = state.get("target_path", "")
    repo_url = state.get("repo_url", "")
    project_language = state.get("project_language", "typescript")
    
    log.info("Input type:      %s", input_type)
    log.info("Target path:     %s", target_path or repo_url)
    log.info("Project language: %s", project_language)
    
    # --- Validate inputs ---
    if not input_type:
        log.error("Missing 'input_type' in state")
        return {"workspace_root": None}
    
    # --- Generate workspace ---
    workspace_id = _generate_workspace_id()
    project_root = _get_project_root()
    workspace_base = _get_workspace_base(project_root, workspace_id)
    
    log.info("Workspace base: %s", workspace_base)
    
    # --- Handle based on input type ---
    result_path: Optional[str] = None
    
    if input_type == "file":
        if not target_path:
            log.error("Missing 'target_path' for file input type")
            return {"workspace_root": None}
        result_path = _handle_file(target_path, workspace_base)
        
    elif input_type == "folder":
        if not target_path:
            log.error("Missing 'target_path' for folder input type")
            return {"workspace_root": None}
        result_path = _handle_folder(target_path, workspace_base)
        
    elif input_type == "repo":
        url = repo_url or target_path
        if not url:
            log.error("Missing 'repo_url' or 'target_path' for repo input type")
            return {"workspace_root": None}
        result_path = _handle_repo(url, workspace_base)
        
    else:
        log.error("Unknown input_type: %s", input_type)
        return {"workspace_root": None}
    
    # --- Check result ---
    if result_path is None:
        log.error("Failed to process %s: %s", input_type, target_path or repo_url)
        return {"workspace_root": None}
    
    log.info("Successfully processed. Workspace: %s", result_path)
    log.end("Clone files node complete")
    
    return {
        "workspace_root": str(result_path),
    }