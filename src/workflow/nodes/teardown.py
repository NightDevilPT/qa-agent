"""
Teardown Node — Phase 6: Finalization
Copies generated tests back to the target project, then safely removes the temporary workspace.
"""

import shutil
from pathlib import Path
from workflow.state import QAState
from utils.logger import get_logger

log = get_logger("teardown")

def teardown(state: QAState) -> dict:
    log.start("Teardown Node — Cleaning up Workspace")

    workspace_root = state.get("workspace_root")
    target_path = state.get("target_path")

    if workspace_root:
        workspace_path = Path(workspace_root)
        temp_dir = workspace_path.parent
        
        # --- NEW: Copy generated tests back to the original project folder ---
        if target_path:
            source_tests_dir = workspace_path / "tests"
            dest_tests_dir = Path(target_path) / "tests"
            
            if source_tests_dir.exists():
                try:
                    # dirs_exist_ok=True allows us to merge with an existing tests folder
                    shutil.copytree(source_tests_dir, dest_tests_dir, dirs_exist_ok=True)
                    log.info("Successfully copied generated tests back to: %s", dest_tests_dir)
                except Exception as e:
                    log.error("Failed to copy generated tests: %s", e)
        
        # --- Clean up the temporary workspace ---
        if temp_dir.exists() and "qa-agent" in temp_dir.name:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
                log.info("Successfully deleted temporary workspace: %s", temp_dir)
            except Exception as e:
                log.error("Failed to delete workspace %s: %s", temp_dir, e)
        else:
            log.warning("Workspace path does not look like a temporary QA directory. Skipping deletion to be safe: %s", temp_dir)
    else:
        log.info("No workspace found to clean up.")

    log.end("Teardown complete")

    return {}