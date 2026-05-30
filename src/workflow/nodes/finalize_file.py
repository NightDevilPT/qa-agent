"""
Level 4: Finalize File Node
Clears the file-specific state variables so the generation loop can move to the next file.
"""
from workflow.state import QAState
from utils.logger import get_logger

log = get_logger("finalize_file")

def finalize_file(state: QAState) -> dict:
    current_file = state.get("current_file")
    log.info("Finalizing work on %s and moving to next file.", current_file)
    
    # Reset all file-specific worker keys
    return {
        "current_file": None,
        "generated_test_code": None,
        "test_output": None,
        "test_file_path": None,
        "retries": 0,
        "test_passed": False
    }