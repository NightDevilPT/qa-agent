"""
Level 4: Test Generation & Self-Healing Node
Pulls the next file from the queue, uses the LLM to generate test cases.
If the test previously failed, it feeds the terminal logs back to the LLM to fix it.
"""

import os
from pathlib import Path
from pydantic import BaseModel, Field

from workflow.state import QAState
from utils.logger import get_logger
from utils.llm import get_llm
from constants.languages.config import get_language_config

log = get_logger("generate_test")

class TestGeneration(BaseModel):
    test_code: str = Field(description="The complete, runnable unit test code.")
    relative_test_path: str = Field(description="The relative path where this test should be saved (e.g., tests/Item.test.js).")

def generate_test(state: QAState) -> dict:
    log.start("generate_test node entered")
    
    todo_list = (state.get("todo_list") or []).copy()
    workspace_root = state.get("workspace_root")
    project_language = state.get("project_language")
    input_type = state.get("input_type", "folder")
    
    current_file = state.get("current_file")
    if not current_file:
        if not todo_list:
            log.warn("Queue is empty. Nothing to generate.")
            return {}
        current_file = todo_list.pop(0)
        log.info("Starting fresh test generation for: %s", current_file)
    else:
        log.warn("Attempting to FIX broken tests for: %s", current_file)

    lang_config = get_language_config(project_language)
    
    # --- BULLETPROOF PATH CALCULATOR ---
    workspace_struct = lang_config["workspace_structure"].get(input_type, {})
    source_dir = workspace_struct.get("source_dir")
    test_dir = workspace_struct.get("test_dir", "tests")
    
    # Calculate how many folders deep the file is to traverse backwards accurately
    depth = len(Path(current_file).parts) - 1
    up_traversal = "../" * (depth + 1)
    
    if source_dir:
        source_path = Path(workspace_root) / source_dir / current_file
        relative_source_path = f"{source_dir}/{current_file}"
        exact_import_string = f"{up_traversal}{source_dir}/{current_file}"
    else:
        source_path = Path(workspace_root) / current_file
        relative_source_path = current_file
        exact_import_string = f"{up_traversal}{current_file}"
        
    # Strip extension for cleaner Node.js imports
    exact_import_string = os.path.splitext(exact_import_string)[0]
    # -----------------------------------

    if not source_path.exists():
        log.error("Source file not found in workspace: %s", source_path)
        return {
            "todo_list": todo_list,
            "current_file": current_file,
            "test_passed": False,
            "retries": state.get("max_retries", 3)
        }

    source_code = source_path.read_text(encoding="utf-8")
    retries = state.get("retries", 0)
    test_output = state.get("test_output", "")
    previous_test_code = state.get("generated_test_code", "")

    # --- UPDATED PROMPT WITH JEST GLOBALS AND STRUCTURE RULES ---
    prompt = f"""
    You are an expert QA Automation Engineer.
    Write a complete, runnable unit test suite using Jest for the following {lang_config['name']} file.
    
    WORKSPACE CONTEXT & RULES:
    1. EXPLICIT JEST IMPORTS: You MUST explicitly import Jest testing functions at the top of the file.
       Example: `import {{ describe, test, expect, beforeEach }} from '@jest/globals';`
    2. SOURCE MODULE IMPORT: You MUST use ES6 `import` syntax (DO NOT use `require`).
       You MUST use exactly this relative path for your import: `{exact_import_string}`
       Example: `import {{ myFunction }} from '{exact_import_string}';`
    3. TEST STRUCTURE: You MUST use nested `describe` blocks for every single function/method.
       Each individual behavior or edge case MUST have its own separate `test` or `it` block.
       DO NOT group multiple different function assertions into a single massive test block.
    
    Source Code ({current_file}):
    ```
    {source_code}
    ```
    """

    if retries > 0 and test_output:
        prompt += f"""
        WARNING: Your previous test execution FAILED. 
        
        Here is the test code you wrote:
        ```
        {previous_test_code}
        ```
        
        Here is the terminal error output from Jest:
        ```
        {test_output}
        ```
        
        Analyze the error carefully. Fix the test code and import paths so it passes successfully.
        """
    else:
        prompt += "\nUse proper testing practices (describe, it/test, expect). Mock external dependencies if necessary."

    try:
        # LLM Call
        llm = get_llm().with_structured_output(TestGeneration)
        result: TestGeneration = llm.invoke(prompt)
        
        log.info("AI successfully generated test code.")

        # Write to Sandbox
        test_file_path = Path(workspace_root) / result.relative_test_path
        test_file_path.parent.mkdir(parents=True, exist_ok=True)
        test_file_path.write_text(result.test_code, encoding="utf-8")
        
        return {
            "todo_list": todo_list,
            "current_file": current_file,
            "generated_test_code": result.test_code,
            "test_file_path": str(test_file_path.relative_to(workspace_root)).replace("\\", "/")
        }

    except Exception as e:
        log.error("Failed to generate tests for %s: %s", current_file, e)
        return {
            "todo_list": todo_list,
            "current_file": current_file,
            "test_passed": False,
            "retries": state.get("max_retries", 3) 
        }