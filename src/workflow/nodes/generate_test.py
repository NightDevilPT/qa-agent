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
    node_tokens = state.get("node_tokens", {})
    
    dependency_graph = state.get("dependency_graph", {})

    current_file = current_status.get("current_file")
    source_code = current_status.get("current_source_code", "")
    retry_count = current_status.get("retries", 0)
    last_error = current_status.get("error_log")

    if not current_file or not workspace_root:
        raise ValueError("Missing 'current_file' or 'workspace_root' in state.")

    # 1. Determine Test File Path - UNIVERSAL MIRRORING
    rel_path = Path(current_file)
    file_stem = rel_path.stem
    file_ext = rel_path.suffix
    test_suffix = f".test{file_ext}"
    
    test_rel_path = Path("tests") / rel_path.parent / f"{file_stem}{test_suffix}"

    # 2. Calculate explicit relative paths for the LLM
    test_dir = test_rel_path.parent
    rel_import_path = os.path.relpath(current_file, test_dir).replace("\\", "/")
    if not rel_import_path.startswith("."):
        rel_import_path = "./" + rel_import_path

    # 3. Build strict path instructions & extract dependency context
    dependencies = dependency_graph.get(current_file, [])
    
    path_instructions = f"CRITICAL PATH REQUIREMENTS:\n"
    path_instructions += f"Your test file will be saved at: `{test_rel_path}`\n"
    path_instructions += f"1. To import the source file being tested, use EXACTLY: `{rel_import_path}`\n"
    path_instructions += "2. Do NOT copy relative import paths directly from the source code. You must adjust them because the test file is in a different directory.\n"
    
    dependency_context = ""
    if dependencies:
        path_instructions += "3. If you need to import internal dependencies, use these calculated paths:\n"
        dependency_context = "Context: Source code of imported dependencies (DO NOT test these, just use them to understand class signatures):\n"
        
        for dep in dependencies:
            dep_rel = os.path.relpath(dep, test_dir).replace("\\", "/")
            if not dep_rel.startswith("."):
                dep_rel = "./" + dep_rel
            path_instructions += f"   - For `{dep}` use: `{dep_rel}`\n"
            
            try:
                dep_path = Path(workspace_root) / dep
                if dep_path.exists():
                    dep_content = dep_path.read_text(encoding="utf-8")
                    if len(dep_content) > 1500:
                        dep_content = dep_content[:1500] + "\n...[TRUNCATED]"
                    dependency_context += f"\n=== {dep} ===\n{dep_content}\n"
            except Exception as e:
                log.warning("Could not read dependency %s for context: %s", dep, e)

    # 4. Extract target edge cases mapped by the planner node
    target_edge_cases = current_status.get("target_edge_cases", [])
    edge_case_instructions = ""
    if target_edge_cases:
        edge_case_instructions = "REQUIRED TEST SCENARIOS:\nYou MUST explicitly write a test case for every single scenario listed below:\n"
        for i, case in enumerate(target_edge_cases, 1):
            edge_case_instructions += f"{i}. {case}\n"

    # 5. Extract Framework Configs
    test_framework = project_analysis.get("test_lib", "jest")
    module_system = project_analysis.get("module_system", "commonjs")

    llm = get_llm(temperature=0.2)
    
    # 6. Build Prompt
    if retry_count == 0:
        log.info("Mode: Fresh Generation for %s", current_file)
        prompt = f"""Role: Senior QA Automation Engineer.
Task: Write a unit test using {test_framework} ({module_system} syntax) for the following file.

File Path: {current_file}
Source Code:
{source_code}

{dependency_context}

{edge_case_instructions}

{path_instructions}

Rules:
1. PURE BLACK-BOX TESTING FOR INTERNAL LOGIC: Do NOT use `vi.mock()`, `jest.mock()`, or `spyOn` for ANY internal files, models, or utilities. Use the real imported implementations.
2. Do NOT assert whether internal utility functions were called. Only assert the final calculated output or state.
3. ONLY mock external I/O (like databases, network requests, or file systems).
4. Return ONLY the raw executable test code.
5. Do not include markdown blocks (no ```javascript)."""

    else:
        log.warning("Mode: Self-Healing (Retry %d) for %s", retry_count, current_file)
        
        previous_test_code = ""
        saved_test_path = file_statuses.get(current_file, {}).get("test_file_path")
        if saved_test_path:
            try:
                previous_test_code = (Path(workspace_root) / saved_test_path).read_text(encoding="utf-8")
            except Exception as e:
                log.warning("Failed to read previous test code: %s", e)

        # --- SMART SELF-HEALING PROMPT ---
        prompt = f"""Role: Senior QA Automation Engineer.
Task: Fix a failing unit test using {test_framework} ({module_system} syntax).

File Path: {current_file}
Source Code:
{source_code}

{dependency_context}

Failing Test Code:
{previous_test_code}

{last_error}  <-- THIS IS THE TARGETED ERROR REPORT FROM THE EXECUTION NODE

{path_instructions}

Rules:
1. FOCUS ONLY ON THE FAILURES: The Targeted Error Report lists specific test scenarios that failed. Fix ONLY those scenarios. 
2. Do NOT delete or alter the test scenarios that are passing successfully.
3. If you see 'NaN' or 'undefined' errors, REMOVE ALL MOCKS AND SPIES for internal models or utilities. Let the real functions run.
4. Return ONLY the raw executable test code.
5. Do not include markdown blocks."""

    # 7. Invoke LLM
    response = llm.invoke(prompt)
    tokens_used = _extract_token_usage(response)
    
    raw_content = response.content
    if isinstance(raw_content, list):
        raw_text = "".join(block.get("text", "") if isinstance(block, dict) else str(block) for block in raw_content)
    else:
        raw_text = str(raw_content)

    test_code = raw_text.replace("```javascript", "").replace("```typescript", "").replace("```", "").strip()

    # 8. Write Test File to Workspace
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
        "total_tokens": total_tokens + tokens_used,
        "node_tokens": {
            **node_tokens,
            "generate_test": node_tokens.get("generate_test", 0) + tokens_used
        }
    }