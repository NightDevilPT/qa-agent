"""Node 1: Interactive Target Ingestion Node.

Handles CLI argument resolution and terminal menu prompts for target mode selection
(Folder Path or Git Repository URL).
"""

from pathlib import Path
from typing import Any, Dict
from src.services.logger_service import logger
from src.services.terminal_service import terminal_service
from src.workflow.state import QAState


def ingest_target_node(state: QAState) -> Dict[str, Any]:
    """Node 1: Interactively prompt user for target path and input mode (FOLDER or GIT_REPO).

    Args:
        state: Active QAState dictionary.

    Returns:
        State update dictionary containing target_path and input_mode.
    """
    logger.info("[Node 1: IngestTarget] Starting target ingestion phase...")

    # 1. Display terminal header and interactive mode selection menu
    terminal_service.display_header(
        title="Autonomous QA Agent System",
        subtitle="LangGraph Automated Test Generation & Sandbox Execution"
    )

    mode_options = [
        {"name": "Folder Path (Generate tests for project directory)", "code": "FOLDER"},
        {"name": "Git Repository URL (Clone public repo and generate tests)", "code": "GIT_REPO"},
    ]

    selected_mode_dict = terminal_service.prompt_select(
        prompt_msg="Select Target Input Mode",
        options=mode_options,
        default_index=0  # Folder Path is default
    )
    input_mode = selected_mode_dict["code"]

    # 2. Prompt user for path / URL based on selected mode
    target_path_str = ""

    if input_mode == "FOLDER":
        while True:
            raw_input = terminal_service.prompt_text(
                prompt_msg="Enter target folder path",
                default="./"
            )
            clean_p = raw_input.strip('\'"')
            p_obj = Path(clean_p).resolve()
            if not p_obj.exists() or not p_obj.is_dir():
                print(f"  Folder path does not exist or is not a directory: '{p_obj}'. Please try again.")
                continue
            target_path_str = str(p_obj)
            break

    elif input_mode == "GIT_REPO":
        while True:
            raw_url = terminal_service.prompt_text(
                prompt_msg="Enter public Git repository URL (https://github.com/...)"
            )
            clean_url = raw_url.strip('\'"')
            if not clean_url.startswith(("http://", "https://", "git@")):
                print("  Invalid Git URL format. Must start with http://, https://, or git@.")
                continue
            target_path_str = clean_url
            break

    logger.info(f"[Node 1: IngestTarget] Ingestion complete: mode='{input_mode}', target='{target_path_str}'")

    terminal_service.display_summary(
        title="Target Ingestion Confirmed",
        items={
            "Input Mode": input_mode,
            "Resolved Target": target_path_str
        }
    )

    return {
        "target_path": target_path_str,
        "input_mode": input_mode
    }
