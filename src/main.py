import sys
import json
from pathlib import Path
from rich.prompt import Prompt
from utils.hitl import ask_human
from utils.logger import console, get_logger
from workflow.graph import compile_graph

log = get_logger("main")

def main():
    try:
        # Prompt for Language
        lang_choice = ask_human(
            options={
                "1": "JavaScript",
                "2": "TypeScript"
            },
            title="Select Project Language",
            description="Choose the language for the target project.",
            style="info"
        )
        
        project_language = "javascript" if lang_choice == "1" else "typescript"

        # Prompt for Input Type
        type_choice = ask_human(
            options={
                "1": "File",
                "2": "Folder",
                "3": "Repository"
            },
            title="Select Input Type",
            description="What type of source are we analyzing?",
            style="info"
        )
        
        type_mapping = {
            "1": "file",
            "2": "folder",
            "3": "repo"
        }
        input_type = type_mapping[type_choice]

        # Prompt for Target Path / URL based on Input Type
        console.print()
        if input_type == "repo":
            user_input = Prompt.ask(
                "[bold cyan]Enter the GitHub repository URL[/bold cyan]", 
                console=console
            )
        else:
            user_input = Prompt.ask(
                f"[bold cyan]Enter the absolute or relative path to the {input_type}[/bold cyan]", 
                console=console
            )

        log.info("Initialization Complete.")
        log.info(f"Language: {project_language}")
        log.info(f"Target Type: {input_type}")
        log.info(f"Input: {user_input}")

        # 1. Build initial state
        initial_state = {
            "input_type": input_type,
            "project_language": project_language,
            "max_retries": 3,
            "target_path": user_input.strip() if input_type != "repo" else None,
            "repo_url": user_input.strip() if input_type == "repo" else None,
        }

        # 2. Compile and run the graph
        app = compile_graph()
        
        log.section("Graph Execution")
        final_state = app.invoke(initial_state)
        
        # 3. Save Stats JSON into the ORIGINAL Target Directory (NOT the temp workspace)
        # Fallback to current working directory (".") if target_path is missing (e.g., repo clone)
        target_dir = final_state.get("target_path") or "."
        stats_file = Path(target_dir) / "qa_agent_stats.json"

        try:
            # Filter out heavy/unnecessary keys to keep the JSON readable
            dump_data = {
                k: v for k, v in final_state.items() 
                if k not in ["current_status", "project_analysis", "workspace_root"]
            }
            
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(dump_data, f, indent=2)
                
            log.info(f"Saved run statistics to: {stats_file}")
        except Exception as e:
            log.error(f"Could not save statistics file: {e}")
            
        log.end("Run completed successfully.")

    except KeyboardInterrupt:
        console.print("\n[bold red]Process interrupted by user. Exiting...[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()