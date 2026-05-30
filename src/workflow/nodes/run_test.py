"""
Level 4: Test Execution Node
Runs the generated test file inside the persistent Docker container.
Captures terminal output and updates the state with pass/fail results.
"""

from workflow.state import QAState
from utils.logger import get_logger
from constants.languages.config import get_language_config
from utils.sandbox import Sandbox

log = get_logger("run_test")

def run_test(state: QAState) -> dict:
    log.start("run_test node entered")
    
    current_file = state.get("current_file")
    test_file_path = state.get("test_file_path")
    container_id = state.get("container_id")
    project_language = state.get("project_language")
    retries = state.get("retries", 0)
    
    # --- SPECIFIC VALIDATION ---
    if not container_id:
        log.error("Validation Failed: 'container_id' is missing from state! Did init_docker fail?")
        return {"test_passed": False, "retries": retries + 1}
        
    if not test_file_path:
        log.error("Validation Failed: 'test_file_path' is missing! The AI likely failed to generate the test code.")
        return {"test_passed": False, "retries": retries + 1}
    # ---------------------------

    lang_config = get_language_config(project_language)
    
    try:
        sandbox = Sandbox()
        log.info("Executing test: %s (Attempt %d)", test_file_path, retries + 1)
        
        container = sandbox.client.containers.get(container_id)
        
        test_cmd = f"npx jest {test_file_path}" if project_language in ["javascript", "typescript"] else lang_config["test_cmd"]
        
        exit_code, output = container.exec_run(["/bin/sh", "-c", test_cmd])
        
        passed = (exit_code == 0)
        output_str = output.decode("utf-8", errors="replace")
        
        if passed:
            log.info("✅ Test Passed for %s!", current_file)
        else:
            log.warn("❌ Test Failed for %s.", current_file)
            log.info("Terminal Output:\n%s", output_str[:500] + ("\n...[TRUNCATED]" if len(output_str) > 500 else ""))
            
        return {
            "test_passed": passed,
            "test_output": output_str,
            "retries": retries + 1
        }

    except Exception as e:
        log.error("Failed to execute test in container: %s", e)
        return {"test_passed": False, "test_output": str(e), "retries": retries + 1}