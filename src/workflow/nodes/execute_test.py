"""
Execute Test Node — Phase 5: Worker Loop
Runs the newly generated test file inside the Docker Sandbox.
"""

from pathlib import Path
from workflow.state import QAState
from utils.logger import get_logger
from utils.sandbox import create_sandbox
from constants.languages.config import get_language_config

log = get_logger("execute_test")

def execute_test(state: QAState) -> dict:
    log.start("Execute Test Node — Running Sandbox")

    workspace_root = state.get("workspace_root")
    project_analysis = state.get("project_analysis", {})
    current_status = state.get("current_status", {})
    file_statuses = state.get("file_statuses", {})
    project_language = state.get("project_language", "javascript")
    max_retries = state.get("max_retries", 3)
    
    current_file = current_status.get("current_file")
    test_path_str = file_statuses.get(current_file, {}).get("test_file_path")
    current_retries = current_status.get("retries", 0)

    if not workspace_root or not current_file or not test_path_str:
        log.error("Missing required state for test execution.")
        return {"current_status": {**current_status, "is_error": True, "error_log": "Internal graph state error."}}

    workspace_path = Path(workspace_root)
    
    base_lang_config = get_language_config(project_language)
    test_lib_config = project_analysis.get("test_lib_config", {})
    raw_test_cmd = test_lib_config.get("per_file_test_cmd", "")
    
    linux_safe_test_path = test_path_str.replace("\\", "/")
    test_cmd = raw_test_cmd.replace("{test_path}", linux_safe_test_path)
    
    docker_config = {
        **base_lang_config,
        "image": "node:20-alpine",
        "test_cmd": test_cmd,
        "install_cmd": ""  
    }
    
    workspace_info = {
        "workspace_dir": workspace_path,
        "config": docker_config,
    }

    sandbox = create_sandbox()
    
    log.info("Executing command: %s", test_cmd)
    try:
        result = sandbox.execute_tests(workspace_info, timeout=120)
        passed = result.get("passed", False)
        
        stdout_text = result.get("stdout", "").strip()
        stderr_text = result.get("stderr", "").strip()
        combined_output = f"{stdout_text}\n{stderr_text}".strip()
        
        # --- BUG FIX: Strict output parsing for swallowed exit codes ---
        # If any of these strings appear in the terminal, the test definitely failed.
        if any(err_string in combined_output for err_string in ["FAIL ", "Failed Suites", "Error:", "No test files found"]):
            passed = False
        
        error_log = combined_output
        if error_log and len(error_log) > 2500:
            error_log = "...[TRUNCATED]\n" + error_log[-2500:]
            
    except Exception as e:
        log.error("Sandbox execution failed: %s", e)
        passed = False
        error_log = f"Sandbox framework crash: {str(e)}"
        combined_output = error_log

    new_retry_count = current_retries + 1 if not passed else current_retries

    if passed:
        log.info("[PASS] Test successful for %s", current_file)
        if combined_output:
            log.info("\n--- Sandbox Terminal Output ---\n%s\n-------------------------------", combined_output)
            
        file_statuses[current_file]["status"] = "completed"
        file_statuses[current_file]["passed"] = True
    else:
        log.warn("[FAIL] Test failed for %s. Attempt %d/%d.", current_file, new_retry_count, max_retries)
        if combined_output:
            log.info("\n--- Sandbox Failure Output ---\n%s\n-------------------------------", combined_output)

        if new_retry_count >= max_retries:
            log.error("[ABORT] Max retries reached. Moving on.")
            file_statuses[current_file]["status"] = "failed"
            file_statuses[current_file]["passed"] = False
            
    file_statuses[current_file]["retries_used"] = new_retry_count

    updated_current_status = {
        **current_status,
        "test_passed": passed,
        "test_output": result.get("stdout", "") if 'result' in locals() else "",
        "error_log": error_log if not passed else None,
        "retries": new_retry_count
    }

    log.end("Test execution complete")
    
    return {
        "current_status": updated_current_status,
        "file_statuses": file_statuses
    }