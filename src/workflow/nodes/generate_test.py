"""
Generate Test Node — Phase 5: Worker Loop
Uses LLM to write or fix test code, writes it to workspace, and updates the ledger.
"""

import os
from pathlib import Path
from workflow.state import QAState
from utils.logger import get_logger
from utils.llm import get_llm

log = get_logger("generate_test")

def _extract_token_usage(response) -> int:
    try:
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata.get("total_tokens", 0)
    except Exception:
        pass
    return 0

def generate_test(state: QAState) -> dict:
    log.start("Generate Test Node — Writing Code")

    workspace_root = state.get("workspace_root")
    project_analysis = state.get("project_analysis", {})
    current_status = state.get("current_status", {})
    file_statuses = state.get("file_statuses", {})
    total_tokens = state.get("total_tokens", 0)

    current_file = current_status.get("current_file")
    source_code = current_status.get("current_source_code", "")
    retry_count = current_status.get("retries", 0)
    last_error = current_status.get("error_log")

    if not current_file or not workspace_root:
        raise ValueError("Missing 'current_file' or 'workspace_root' in state.")

    # 1. Determine Test File Path
    rel_path = Path(current_file)
    file_stem = rel_path.stem
    file_ext = rel_path.suffix
    test_suffix = f".test{file_ext}"
    
    if "src" in rel_path.parts:
        test_rel_path = Path(*["tests" if p == "src" else p for p in rel_path.parts]).with_name(f"{file_stem}{test_suffix}")
    else:
        test_rel_path = Path("tests") / rel_path.with_name(f"{file_stem}{test_suffix}")

    # --- BUG FIX: Calculate exact JS import path ---
    # Calculates the relative path from the test file directory back to the source file
    test_dir = test_rel_path.parent
    rel_import_path = os.path.relpath(current_file, test_dir)
    rel_import_path = rel_import_path.replace("\\", "/") # Ensure JS-safe forward slashes
    if not rel_import_path.startswith("."):
        rel_import_path = "./" + rel_import_path

    # 2. Extract Framework Configs
    test_framework = project_analysis.get("test_lib", "jest")
    module_system = project_analysis.get("module_system", "commonjs")

    llm = get_llm(temperature=0.2)
    
    # 3. Build Prompt
    if retry_count == 0:
        log.info("Mode: Fresh Generation for %s", current_file)
        prompt = f"""Role: Senior QA Automation Engineer.
Task: Write a unit test using {test_framework} ({module_system} syntax) for the following file.

File Path: {current_file}
Source Code:
{source_code}

CRITICAL REQUIREMENT: Your test file will be saved at `{test_rel_path}`. 
You MUST import the source code using this exact relative path: `{rel_import_path}`

Rules:
1. Return ONLY the raw executable test code.
2. Do not include markdown blocks (no ```javascript)."""

    else:
        log.warning("Mode: Self-Healing (Retry %d) for %s", retry_count, current_file)
        
        previous_test_code = ""
        saved_test_path = file_statuses.get(current_file, {}).get("test_file_path")
        if saved_test_path:
            try:
                previous_test_code = (Path(workspace_root) / saved_test_path).read_text(encoding="utf-8")
            except Exception as e:
                log.warning("Failed to read previous test code: %s", e)

        prompt = f"""Role: Senior QA Automation Engineer.
Task: Fix a failing unit test using {test_framework} ({module_system} syntax).

File Path: {current_file}
Source Code:
{source_code}

Failing Test Code:
{previous_test_code}

Error Output:
{last_error}

CRITICAL REQUIREMENT: Your test file will be saved at `{test_rel_path}`. 
You MUST import the source code using this exact relative path: `{rel_import_path}`

Rules:
1. Analyze the error and fix the test code.
2. Return ONLY the raw executable test code.
3. Do not include markdown blocks."""

    # 4. Invoke LLM
    response = llm.invoke(prompt)
    tokens_used = _extract_token_usage(response)
    
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_text = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in raw_content)
    else:
        raw_text = str(raw_content)

    test_code = raw_text.replace("```javascript", "").replace("```typescript", "").replace("```", "").strip()

    # 5. Write Test File to Workspace
    test_path_full = Path(workspace_root) / test_rel_path
    test_path_full.parent.mkdir(parents=True, exist_ok=True)
    test_path_full.write_text(test_code, encoding="utf-8")

    log.info("Wrote test file to: %s", test_rel_path)
    log.end("Test generation complete")

    current_file_ledger = file_statuses.get(current_file, {})
    current_file_ledger["test_file_path"] = str(test_rel_path)
    current_file_ledger["tokens_used"] = current_file_ledger.get("tokens_used", 0) + tokens_used
    file_statuses[current_file] = current_file_ledger

    return {
        "file_statuses": file_statuses,
        "total_tokens": total_tokens + tokens_used
    }