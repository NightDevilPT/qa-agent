"""
QA Agent CLI entry point.
Collects user inputs, builds the initial state, triggers the LangGraph orchestrator,
and dumps the final state.
"""

import sys
import json
from pathlib import Path

from rich.prompt import Prompt, IntPrompt

from constants.languages.config import get_language_config
from utils.logger import console, get_logger
from utils.hitl import ask_human
from workflow import compile_graph

# Use only the custom logger for all outputs
log = get_logger("main")


def main() -> None:
    """Run the LangGraph workflow with user-provided parameters."""
    log.section("Autonomous QA Agent Initialization")

    # 1. Collect Project Language using HITL (Default: JavaScript Project)
    project_language_choice = ask_human(
        options={
            "1": "JavaScript Project (Node/Jest)",
            "2": "TypeScript Project (ts-jest)"
        },
        title="Project Language",
        description="Select the language of the repository you want to test.",
        default="1",
        style="info"
    )
    project_language = "javascript" if project_language_choice == "1" else "typescript"
    lang_config = get_language_config(project_language)

    # 2. Collect Input Type using HITL
    input_type_choice = ask_human(
        options={
            "1": "Single File",
            "2": "Directory Tree",
            "3": "Full Repository (Clone)"
        },
        title="Input Type",
        description="Are we testing a specific file or scanning a whole folder?",
        default="2",
        style="info"
    )
    input_type_map = {
        "1": "file",
        "2": "folder",
        "3": "repo"
    }
    input_type = input_type_map[input_type_choice]

    # 3. Collect Target Path (using rich Prompt for CLI validation)
    console.print()
    raw_path = Prompt.ask(
        f"[bold]Enter the path to your {input_type}[/bold]",
        default=".",
        console=console
    ).strip()
    
    is_url = raw_path.startswith(("http://", "https://", "git@"))

    if is_url:
        target = raw_path
        if input_type != "repo":
            log.warn("Target is a URL; overriding input_type to 'repo'")
            input_type = "repo"
    else:
        target_path = Path(raw_path).expanduser().resolve()
        if not target_path.exists():
            log.error("Path not found: %s", target_path)
            sys.exit(1)
        target = str(target_path)

        # Auto-correct input_type if there's a mismatch
        if target_path.is_file() and input_type != "file":
            log.warn("Target is a file; overriding input_type to 'file'")
            input_type = "file"
        elif target_path.is_dir() and input_type == "file":
            log.warn("Target is a directory; overriding input_type to 'folder'")
            input_type = "folder"

    # 4. Collect Max Retries
    console.print()
    max_retries = IntPrompt.ask(
        "[bold]Max self-healing retries per file[/bold]",
        default=3,
        console=console
    )

    # --- Graph Execution ---
    log.section("QA AGENT RUN")
    log.start(
        "Orchestrator started path=%s input_type=%s language=%s retries=%d",
        target,
        input_type,
        project_language,
        max_retries
    )

    # Build the initial QAState
    initial_state = {
        "target_path": str(target),
        "input_type": input_type,
        "project_language": project_language,
        "max_retries": max_retries,
    }

    try:
        # Compile and invoke the LangGraph
        graph = compile_graph()
        result = graph.invoke(initial_state)
    except Exception as e:
        log.error("Workflow crashed unexpectedly: %s", e)
        sys.exit(1)

    # --- State Dump ---
    log.section("Final Graph State Dump")
    
    # Print to console
    state_dump = json.dumps(result, indent=2, default=str)
    log.info("\n%s", state_dump)

    # Save to JSON file in the target directory
    try:
        # We use result.get() because if it was a URL, clone_repo changed target_path to a local temp folder
        final_target_path = Path(result.get("target_path", "."))
        
        # If the target was a single file, save the JSON in its parent folder
        output_dir = final_target_path.parent if final_target_path.is_file() else final_target_path
        output_file = output_dir / "qa_agent_state.json"
        
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
            
        log.info("💾 State successfully saved to: %s", output_file)
    except Exception as e:
        log.warn("Failed to save state JSON file: %s", e)

    # --- Summary Output ---
    log.section("File Discovery Summary")
    discovered = result.get("discovered_files") or []
    
    if discovered:
        for index, file_path in enumerate(discovered, start=1):
            log.info("%d | %s", index, file_path)
    else:
        log.warn("No valid test candidates found in the specified path.")

    # Final footer stats
    log.end("Orchestrator finished. Discovered_files=%d", len(discovered))
    console.print()
    log.info(
        "Run Stats -> Root: %s | Language: %s | Mode: %s | Count: %d | Tokens: %d",
        target,
        lang_config['name'],
        input_type,
        len(discovered),
        result.get("total_tokens", 0)
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print()
        log.warn("Run cancelled by user.")
        sys.exit(0)