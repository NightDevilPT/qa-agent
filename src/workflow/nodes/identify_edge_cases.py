"""
Identify Edge Cases Node — Phase 5: Worker Loop (Pre-Generation)
Analyzes the active file and generates a strict checklist of happy paths and edge cases.
"""

from pathlib import Path
from typing import List
from pydantic import BaseModel, Field

from workflow.state import QAState
from utils.logger import get_logger
from utils.llm import get_llm

log = get_logger("identify_edge_cases")

# --- Structured Output Model ---
class EdgeCasePlan(BaseModel):
    scenarios: List[str] = Field(
        description="A detailed list of test scenarios, including both happy paths and edge cases (e.g., 'should throw an error if price is negative')."
    )

def _extract_token_usage(response) -> int:
    try:
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            return response.usage_metadata.get("total_tokens", 0)
    except Exception:
        pass
    return 0

def identify_edge_cases(state: QAState) -> dict:
    log.start("Identify Edge Cases Node — Planning Scenarios")

    current_status = state.get("current_status", {})
    file_statuses = state.get("file_statuses", {})
    total_tokens = state.get("total_tokens", 0)
    node_tokens = state.get("node_tokens", {})

    current_file = current_status.get("current_file")
    source_code = current_status.get("current_source_code", "")

    # If retries > 0, we already have edge cases, no need to regenerate them.
    if current_status.get("retries", 0) > 0:
        log.info("Self-healing mode active. Re-using existing edge cases.")
        return {}

    if not current_file or not source_code:
        log.warning("No active file or source code found. Skipping edge case generation.")
        return {}

    llm = get_llm(temperature=0.2)
    structured_llm = llm.with_structured_output(EdgeCasePlan, include_raw=True)

    prompt = f"""Role: Senior QA Architect.
Task: Review the following source code and identify ALL necessary unit test scenarios.
You must cover:
1. The Happy Path (expected standard behavior).
2. Edge Cases (null values, negative numbers, missing arguments, empty arrays, etc.).
3. Error handling (exceptions thrown).

File Path: {current_file}
Source Code:
{source_code}

Provide a comprehensive list of what needs to be tested."""

    # Invoke LLM
    response = structured_llm.invoke(prompt)
    parsed: EdgeCasePlan = response["parsed"]
    tokens_used = _extract_token_usage(response["raw"])
    
    edge_cases_list = parsed.scenarios
    log.info("Identified %d edge cases for %s", len(edge_cases_list), current_file)
    for ec in edge_cases_list:
        log.info("  - %s", ec)

    # Prepare the dictionary for the ledger (FileStatus)
    edge_cases_dict = {}
    for case in edge_cases_list:
        edge_cases_dict[case] = {"status": "planned"}

    # Update state
    updated_current_status = {
        **current_status,
        "target_edge_cases": edge_cases_list
    }

    current_file_ledger = file_statuses.get(current_file, {})
    current_file_ledger["edge_cases"] = edge_cases_dict
    file_statuses[current_file] = current_file_ledger

    log.end("Edge case identification complete")

    return {
        "current_status": updated_current_status,
        "file_statuses": file_statuses,
        "total_tokens": total_tokens + tokens_used,
        "node_tokens": {
            **node_tokens,
            "identify_edge_cases": node_tokens.get("identify_edge_cases", 0) + tokens_used
        }
    }