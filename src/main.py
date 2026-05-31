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
        
        # 3. Save Stats JSON into Workspace Root
        workspace_root = final_state.get("workspace_root")
        if workspace_root:
            workspace_path = Path(workspace_root)
            
            # Extract key statistics from the final state
            run_stats = {
                "discovered_files_count": len(final_state.get("discovered_files", [])),
                "discovered_files": final_state.get("discovered_files", []),
                "project_analysis": final_state.get("project_analysis", {}),
                "total_tokens": final_state.get("total_tokens", 0),
                "node_tokens": final_state.get("node_tokens", {}),
                "file_statuses": final_state.get("file_statuses", {}),
                "meta": final_state
            }
            
            # Write to qa_agent_stats.json in the workspace root
            stats_file = workspace_path / "qa_agent_stats.json"
            with open(stats_file, "w", encoding="utf-8") as f:
                json.dump(run_stats, f, indent=2)
                
            log.info(f"Saved run statistics to: {stats_file}")
            
        log.end("Run completed successfully.")

    except KeyboardInterrupt:
        console.print("\n[bold red]Process interrupted by user. Exiting...[/bold red]")
        sys.exit(1)

if __name__ == "__main__":
    main()