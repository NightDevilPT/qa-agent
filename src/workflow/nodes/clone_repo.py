import shutil
import subprocess
import tempfile
from pathlib import Path

from workflow.state import QAState
from utils.logger import get_logger

# Rulebook §2: Use get_logger
log = get_logger("clone_repo")

def clone_repo(state: QAState) -> dict:
    """
    Clones the target GitHub URL into a local folder.
    Overwrites 'target_path' in the state with the new local path.
    """
    log.start("clone_repo node entered")
    
    repo_url = state.get("target_path")
    
    # Failsafe check
    if not repo_url or not str(repo_url).startswith(("http://", "https://", "git@")):
        log.error("Expected a valid Git URL in target_path, got: %s", repo_url)
        # If it fails, we return an empty dict so we don't break the state, 
        # though this will likely cause extract_files to fail gracefully later.
        return {}

    # Create a persistent temporary directory inside the workspace root under '.temp'
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    temp_base = project_root / ".temp"
    temp_base.mkdir(exist_ok=True)
    temp_dir = tempfile.mkdtemp(prefix="qa_agent_repo_", dir=str(temp_base))
    local_target = Path(temp_dir).resolve()
    
    try:
        log.info("Cloning remote repository: %s", repo_url)
        # Run standard git clone command (depth 1 for speed)
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(local_target)],
            capture_output=True,
            text=True,
            check=True
        )
        
        log.end("Successfully cloned to local temp folder: %s", local_target)
        
        # CRITICAL: We update the state so all future nodes (extract_files, init_docker)
        # use this local path instead of the URL.
        return {"target_path": str(local_target)}
        
    except subprocess.CalledProcessError as e:
        log.error("Failed to clone repository. Git stderr: %s", e.stderr.strip())
        shutil.rmtree(local_target, ignore_errors=True)
        raise RuntimeError(f"Could not clone repository: {repo_url}") from e
    except FileNotFoundError:
        log.error("'git' command not found. Is Git installed on this machine?")
        shutil.rmtree(local_target, ignore_errors=True)
        raise RuntimeError("Git is not installed or not in PATH.")