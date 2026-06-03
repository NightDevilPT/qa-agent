"""
Select Next File Node — Phase 5: Worker Loop
Pops the next PENDING file from the todo list and sets it as the active work item.
"""

from pathlib import Path
from workflow.state import QAState
from utils.logger import get_logger

log = get_logger("select_next_file")

def select_next_file(state: QAState) -> dict:
    log.start("Select Next File Node — Queue Manager")

    todo_list = state.get("todo_list", [])
    file_statuses = state.get("file_statuses", {})
    workspace_root = state.get("workspace_root")

    next_file = None
    
    # 1. Find the first pending file
    for file_path in todo_list:
        if file_statuses.get(file_path, {}).get("status") == "pending":
            next_file = file_path
            break

    if next_file:
        log.info("Selected next file for testing: %s", next_file)
        
        # 2. Update the ledger (FileStatus)
        file_statuses[next_file]["status"] = "in_progress"
        
        # 3. Read the source code to store in active memory
        source_code = None
        if workspace_root:
            try:
                source_code = (Path(workspace_root) / next_file).read_text(encoding="utf-8", errors="replace")
            except Exception as e:
                log.warning("Could not read source file %s: %s", next_file, e)

        # 4. Strictly adhere to CurrentFileStatus TypedDict
        updated_current_status = {
            "current_file": next_file,
            "current_source_code": source_code,
            "test_passed": False,
            "test_output": None,
            "retries": 0,
            "is_error": False,
            "error_log": None
        }
    else:
        log.info("No pending files left in the queue.")
        # Reset state cleanly if queue is empty
        updated_current_status = {
            "current_file": None,
            "current_source_code": None,
            "test_passed": False,
            "test_output": None,
            "retries": 0,
            "is_error": False,
            "error_log": None
        }

    log.end("Queue selection complete")

    return {
        "file_statuses": file_statuses,
        "current_status": updated_current_status
    }