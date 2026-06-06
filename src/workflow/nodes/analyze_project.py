"""
Analyze Project Node — Phase 2: Project Analysis

Uses LLM with structured output to analyze the workspace and determine:
  1. Which files to inspect for project setup (package.json, configs, etc.)
  2. What test framework is used (or should be used)
  3. Module system (ESM vs CommonJS)
  4. Project dependencies
  5. Test framework configuration
"""

from pathlib import Path
from typing import List, Dict
from pydantic import BaseModel, Field

# Local module imports
from workflow.state import QAState
from utils.logger import get_logger
from utils.llm import get_llm, extract_token_usage

log = get_logger("analyze_project")


# ================================================================
# Pydantic Models for Structured LLM Output
# ================================================================

class SetupFilesOutput(BaseModel):
    setup_files: List[str] = Field(
        default_factory=list,
        description="List of file paths containing project setup information"
    )

class TestLibConfigOutput(BaseModel):
    name: str = Field(description="Framework name: jest, vitest, mocha, or jasmine")
    install_packages: Dict[str, str] = Field(description="Packages to install with versions, e.g. {'jest': '^29.7.0'}")
    config_files: Dict[str, str] = Field(description="Config file name to content mapping")
    per_file_test_cmd: str = Field(description="Command to run a single test file, use {test_path} placeholder")

class ProjectAnalysisOutput(BaseModel):
    has_package_json: bool = Field(description="Whether a package.json file exists")
    test_lib: str = Field(description="Detected test framework: jest, vitest, mocha, jasmine, or none")
    module_system: str = Field(description="Module system: esm, commonjs, or mixed")
    project_dependencies: Dict[str, str] = Field(default_factory=dict, description="Dependencies from package.json")
    test_lib_config: TestLibConfigOutput = Field(description="Test framework configuration details")


# ================================================================
# Main Node Entrypoint
# ================================================================

def analyze_project(state: QAState) -> dict:
    """
    Main LangGraph Node function.
    Executes a two-step LLM extraction process inline to minimize function overhead.
    """
    log.start("Analyze Project Node — Phase 2: Project Analysis")

    workspace_root = state.get("workspace_root")
    file_list = state.get("file_to_be_process", [])
    project_language = state.get("project_language", "typescript")
    total_tokens = state.get("total_tokens", 0)
    node_tokens = state.get("node_tokens", {})

    if not workspace_root or not file_list:
        raise ValueError("State is missing required 'workspace_root' or 'file_to_be_process'")

    # Use temperature 0.0 for strict, deterministic data extraction
    llm = get_llm(temperature=0.0)
    node_token_count = 0

    # ----------------------------------------------------------------
    # Step 1: Identify Setup Files
    # ----------------------------------------------------------------
    log.section("Step 1: Identifying setup files")
    
    # TOKEN OPTIMIZATION: Filter out deeply nested source files before prompting.
    # We only care about root-level files, json/js/ts config files, and hidden rc files.
    config_extensions = ('.json', '.js', '.ts', '.cjs', '.mjs', 'rc')
    likely_configs = [
        f for f in file_list 
        if f.endswith(config_extensions) and (f.count('/') < 2 or 'config' in f.lower())
    ]
    target_files = likely_configs if likely_configs else file_list

    prompt_1 = f"""Role: QA Architect.
Task: Identify core setup files required to understand automated testing configurations.
Look specifically for: package.json, compiler configs (tsconfig), and test/build configs.

Available Files:
{chr(10).join(f"- {f}" for f in target_files)}"""

    step1_llm = llm.with_structured_output(SetupFilesOutput, include_raw=True)
    step1_response = step1_llm.invoke(prompt_1)
    
    setup_files = step1_response["parsed"].setup_files
    node_token_count += extract_token_usage(step1_response["raw"])
    log.info("Identified %d setup files: %s", len(setup_files), setup_files)

    if not setup_files:
        log.warning("No setup files found. Returning empty analysis.")
        return {
            "project_analysis": {},
            "total_tokens": total_tokens + node_token_count,
            "node_tokens": {**node_tokens, "analyze_project": node_token_count}
        }

    # ----------------------------------------------------------------
    # Step 2: Read Files & Analyze Project Context
    # ----------------------------------------------------------------
    log.section("Step 2: Analyzing project setup")
    
    files_text = ""
    for file_path in setup_files:
        full_path = Path(workspace_root) / file_path
        try:
            if full_path.is_file():
                content = full_path.read_text(encoding="utf-8", errors="replace")
                # TOKEN OPTIMIZATION: Truncate to 2500 chars. Configs rarely need more context.
                files_text += f"\n=== {file_path} ===\n{content[:2500]}\n"
        except Exception as e:
            log.warning("Could not read %s: %s", file_path, e)

    if not files_text.strip():
        raise ValueError("Critical Failure: Could not read any identified setup files.")

    prompt_2 = f"""Role: QA Architect.
Task: Analyze project configurations and determine the optimal test framework setup.
Project Language: {project_language}

Project Files:
{files_text}

Extraction Rules:
1. test_lib: Detect jest/vitest/mocha/jasmine in dependencies. Default to 'jest' if none found.
2. module_system: Read package.json "type" field ("module"=esm, "commonjs"=commonjs). Default: commonjs.
3. install_packages: Exact package names and versions needed for the test framework.
4. config_files: Provide the minimal required configuration file content.
5. per_file_test_cmd: CLI command to run a single test file (must include {{test_path}} placeholder)."""

    step2_llm = llm.with_structured_output(ProjectAnalysisOutput, include_raw=True)
    step2_response = step2_llm.invoke(prompt_2)
    
    analysis: ProjectAnalysisOutput = step2_response["parsed"]
    node_token_count += extract_token_usage(step2_response["raw"])

    log.info("Test framework: %s", analysis.test_lib)
    log.info("Module system:  %s", analysis.module_system)
    log.info("Dependencies:   %d", len(analysis.project_dependencies))
    log.info("Total tokens:   %d", node_token_count)
    log.end("Analyze project complete")

    return {
        "project_analysis": analysis.model_dump(),
        "total_tokens": total_tokens + node_token_count,
        "node_tokens": {
            **node_tokens,
            "analyze_project": node_token_count,
        },
    }