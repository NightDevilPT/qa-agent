"""
Execute Test Node — Phase 5: Worker Loop
Runs the newly generated test file inside the Docker Sandbox.
Parses the output to update the edge case ledger and isolates specific failures.
"""

from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

from workflow.state import QAState
from utils.logger import get_logger
from utils.sandbox import create_sandbox
from utils.llm import get_llm
from constants.languages.config import get_language_config

log = get_logger("execute_test")

# --- Structured Output Models for Error Parsing ---
class FailedScenario(BaseModel):
    test_name: str = Field(description="The exact name or description of the test scenario that failed.")
    error_details: str = Field(description="The specific assertion error, stack trace, or reason it failed.")

class TestParserOutput(BaseModel):
    failed_scenarios: List[FailedScenario] = Field(
        default_factory=list, 
        description="List of all failed tests extracted from the terminal output."
    )

def _extract_token_usage(response) -> int:
    try:
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata.get("total_tokens", 0)
    except Exception:
        pass
    return 0

def execute_test(state: QAState) -> dict:
    log.start("Execute Test Node — Running Sandbox & Parsing Results")

    workspace_root = state.get("workspace_root")
    project_analysis = state.get("project_analysis", {})
    current_status = state.get("current_status", {})
    file_statuses = state.get("file_statuses", {})
    project_language = state.get("project_language", "javascript")
    max_retries = state.get("max_retries", 3)
    total_tokens = state.get("total_tokens", 0)
    node_tokens = state.get("node_tokens", {})
    
    current_file = current_status.get("current_file")
    test_path_str = file_statuses.get(current_file, {}).get("test_file_path")
    current_retries = current_status.get("retries", 0)
    target_edge_cases = current_status.get("target_edge_cases", [])

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
        
        # --- Strict output parsing for partial failures ---
        failure_indicators = ["FAIL ", "Failed Suites", "Error:", "No test files found", "failing", "✕", "ERR!"]
        if any(err_string in combined_output for err_string in failure_indicators):
            passed = False
            
    except Exception as e:
        log.error("Sandbox execution failed: %s", e)
        passed = False
        combined_output = f"Sandbox framework crash: {str(e)}"

    new_retry_count = current_retries + 1 if not passed else current_retries
    
    focused_error_log = None
    llm_tokens = 0

    # Retrieve the ledger for this file so we can update edge case statuses
    current_file_ledger = file_statuses.get(current_file, {})
    edge_cases_ledger = current_file_ledger.get("edge_cases", {})

    if passed:
        log.info("[PASS] All tests successful for %s", current_file)
        
        # Mark all planned edge cases as PASSED in the ledger
        for case_name in edge_cases_ledger.keys():
            edge_cases_ledger[case_name]["status"] = "passed"
            
        current_file_ledger["status"] = "completed"
        current_file_ledger["passed"] = True
    else:
        log.warn("[FAIL] Tests failed for %s. Attempt %d/%d.", current_file, new_retry_count, max_retries)
        
        # --- SMART FAILURE PARSING ---
        # Instead of dumping the whole terminal, we ask the LLM to extract exactly what failed.
        log.info("Parsing terminal output to isolate failed scenarios...")
        llm = get_llm(temperature=0.0)
        structured_llm = llm.with_structured_output(TestParserOutput, include_raw=True)
        
        # Protect context window
        terminal_tail = combined_output[-3000:] if len(combined_output) > 3000 else combined_output
        
        parse_prompt = f"""Role: QA Test Analyzer.
Task: Read the following test runner terminal output and extract ONLY the tests that failed.
Ignore any passing tests. Extract the specific assertion error or reason for failure.

Terminal Output:
{terminal_tail}"""

        response = structured_llm.invoke(parse_prompt)
        llm_tokens = _extract_token_usage(response["raw"])
        parsed_failures: TestParserOutput = response["parsed"]
        
        # Build the Targeted Error Report for the generate_test node
        if parsed_failures.failed_scenarios:
            focused_error_log = "TARGETED ERROR REPORT (Only fix these scenarios):\n"
            for fail in parsed_failures.failed_scenarios:
                focused_error_log += f"\n❌ Failed Scenario: {fail.test_name}\n   Error: {fail.error_details}\n"
                
                # Try to map the failure back to the ledger to mark it as failed
                # (Simple substring match to update the JSON ledger)
                for case_name in edge_cases_ledger.keys():
                    if fail.test_name.lower() in case_name.lower() or case_name.lower() in fail.test_name.lower():
                        edge_cases_ledger[case_name]["status"] = "failed"
                        edge_cases_ledger[case_name]["last_error"] = fail.error_details
        else:
            # Fallback if the LLM couldn't parse specific tests (e.g., syntax error crash)
            focused_error_log = "CRITICAL SUITE FAILURE (Check for syntax or import errors):\n" + terminal_tail

        # Mark tests that didn't fail as passed in the ledger
        for case_name, data in edge_cases_ledger.items():
            if data.get("status") == "planned":
                data["status"] = "passed"

        if new_retry_count >= max_retries:
            log.error("[ABORT] Max retries reached. Moving on.")
            current_file_ledger["status"] = "failed"
            current_file_ledger["passed"] = False

    # Update state
    current_file_ledger["retries_used"] = new_retry_count
    current_file_ledger["edge_cases"] = edge_cases_ledger
    file_statuses[current_file] = current_file_ledger

    updated_current_status = {
        **current_status,
        "test_passed": passed,
        "test_output": result.get("stdout", "") if 'result' in locals() else "",
        "error_log": focused_error_log, # We pass the FOCUSED error back, not the whole terminal!
        "retries": new_retry_count
    }

    log.end("Test execution & parsing complete")
    
    return {
        "current_status": updated_current_status,
        "file_statuses": file_statuses,
        "total_tokens": total_tokens + llm_tokens,
        "node_tokens": {
            **node_tokens,
            "execute_test": node_tokens.get("execute_test", 0) + llm_tokens
        }
    }