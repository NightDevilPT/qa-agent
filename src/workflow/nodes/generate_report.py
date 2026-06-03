"""
Generate Report Node — Phase 6: Finalization
Compiles the final summary of the entire QA run based on the ledger.
"""

from workflow.state import QAState
from utils.logger import get_logger

log = get_logger("generate_report")

def generate_report(state: QAState) -> dict:
    log.start("Generate Report Node — Summarizing Results")

    file_statuses = state.get("file_statuses", {})
    total_tokens = state.get("total_tokens", 0)
    project_analysis = state.get("project_analysis", {})
    
    test_framework = project_analysis.get("test_lib", "Unknown")

    total_files = len(file_statuses)
    passed = 0
    failed = 0
    total_retries = 0

    # Build per-file breakdown
    file_details = []
    
    for file_path, data in file_statuses.items():
        status = data.get("status")
        is_pass = data.get("passed", False)
        retries = data.get("retries_used", 0)
        
        if is_pass:
            passed += 1
            status_icon = "✅ PASS"
        else:
            failed += 1
            status_icon = "❌ FAIL"
            
        total_retries += retries
        
        file_details.append(
            f"  • {file_path}\n"
            f"    Status: {status_icon} | Retries: {retries} | Tokens: {data.get('tokens_used', 0)}\n"
            f"    Test File: {data.get('test_file_path', 'N/A')}"
        )

    # Format the final report string
    report_lines = [
        "==================================================",
        "             QA AGENT FINAL REPORT                ",
        "==================================================",
        f"Framework:       {test_framework.capitalize()}",
        f"Files Processed: {total_files}",
        f"Passed:          {passed}",
        f"Failed:          {failed}",
        f"Total Retries:   {total_retries}",
        f"Total Tokens:    {total_tokens}",
        "--------------------------------------------------",
        "FILE BREAKDOWN:",
        "\n".join(file_details) if file_details else "  No files processed.",
        "=================================================="
    ]
    
    final_report_str = "\n".join(report_lines)
    
    log.info("\n" + final_report_str)
    log.end("Report generation complete")

    return {
        "final_report": final_report_str
    }