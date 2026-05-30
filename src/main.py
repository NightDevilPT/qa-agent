"""QA Agent CLI entry point."""

import sys
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

from constants.languages.config import get_language_config, normalize_project_language
from utils.logger import console, get_logger
from workflow import compile_graph

log = get_logger("main")


def _prompt_project_language() -> str:
    """Ask user whether the project is JavaScript or TypeScript."""
    raw = Prompt.ask(
        "Project language [javascript/typescript] (js or ts)",
        console=console,
    ).strip()

    if not raw:
        console.print("[red]Project language is required.[/red]")
        sys.exit(1)

    try:
        return normalize_project_language(raw)
    except ValueError as e:
        console.print(f"[red]{e}[/red]")
        sys.exit(1)


def main() -> None:
    """Run the LangGraph workflow with user-provided path."""
    console.print(
        Panel.fit(
            "[bold cyan]QA Agent[/bold cyan]\n[dim]LangGraph | File discovery[/dim]",
            border_style="cyan",
        )
    )

    project_language = _prompt_project_language()
    lang_config = get_language_config(project_language)

    raw_path = Prompt.ask("Enter file or folder path", console=console).strip()
    if not raw_path:
        console.print("[red]No path provided.[/red]")
        sys.exit(1)

    target = Path(raw_path).expanduser().resolve()
    if not target.exists():
        console.print(f"[red]Path not found: {target}[/red]")
        sys.exit(1)

    input_type = "file" if target.is_file() else "folder"
    log.section("QA AGENT RUN")
    log.start(
        "Orchestrator started path=%s input_type=%s project_language=%s",
        target,
        input_type,
        project_language,
    )

    graph = compile_graph()
    result = graph.invoke(
        {
            "target_path": str(target),
            "input_type": input_type,
            "project_language": project_language,
            "max_retries": 3,
        }
    )

    discovered = result.get("discovered_files") or []
    log.end("Orchestrator finished discovered_files=%d", len(discovered))

    console.print()
    table = Table(title="Discovery summary", show_header=True, header_style="bold")
    table.add_column("#", style="dim", width=6)
    table.add_column("Path", style="cyan")

    for index, file_path in enumerate(discovered, start=1):
        table.add_row(str(index), file_path)

    console.print(table)
    console.print(
        f"\n[dim]Root[/dim] {target}  [dim]|[/dim]  "
        f"[dim]Language[/dim] {lang_config['name']}  [dim]|[/dim]  "
        f"[dim]Mode[/dim] {input_type}  [dim]|[/dim]  "
        f"[dim]Count[/dim] {len(discovered)}"
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled.[/yellow]")
        sys.exit(0)
