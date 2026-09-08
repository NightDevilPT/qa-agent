"""Root Entrypoint & Execution Trigger for Autonomous QA Agent.

Triggers the LangGraph state graph pipeline via uv run main.py.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Ensure project root directory is in sys.path
sys.path.insert(0, str(Path(__file__).parent.resolve()))

from src.services.logger_service import get_logger
from src.services.terminal_service import terminal_service
from src.workflow.graph import run_qa_agent

logger = get_logger("Main")


def main() -> None:
    """Launch the Autonomous QA Agent State Machine pipeline."""
    llm_provider = os.getenv("LLM_PROVIDER", "docker").upper()
    terminal_service.display_header(
        title="AUTONOMOUS QA AGENT SYSTEM",
        subtitle=f"LangGraph Automated Test Generation & Sandbox Execution | Active LLM Provider: {llm_provider}",
    )
    logger.info(f"Active LLM Provider: {llm_provider}")

    try:
        logger.info("Executing Autonomous QA Agent LangGraph Pipeline...")
        final_state = run_qa_agent()
        run_id = final_state.get("run_id", "N/A")
        ws_dir = final_state.get("workspace_dir", "N/A")
        logger.success(f"Pipeline Completed Successfully! Run ID: '{run_id}'")
        logger.info(f"Target Path:    {final_state.get('target_path', 'N/A')}")
        logger.info(f"Workspace Dir:  {ws_dir}")
    except KeyboardInterrupt:
        logger.warning("\nExecution cancelled by user.")
    except Exception as e:
        logger.error(f"Unhandled execution error: {e}")
        raise e


if __name__ == "__main__":
    main()
