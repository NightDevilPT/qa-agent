"""QA Agent entry point - Automated test generation for JS/TS."""

import sys
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm

from utils import ask_human, get_llm, create_sandbox
from constants.languages import detect_language, get_language_config

console = Console()
MAX_RETRIES = 3


def clean_test_code(code: str) -> str:
    """Remove markdown code blocks from LLM response."""
    if "```" in code:
        parts = code.split("```")
        code = parts[1] if len(parts) > 1 else parts[0]
        for prefix in ["typescript", "ts", "javascript", "js", "jest"]:
            if code.startswith(prefix):
                lines = code.split("\n")
                code = "\n".join(lines[1:]) if len(lines) > 1 else code
                break
        code = code.strip()
    return code


def read_source_file(file_path: Path) -> str:
    """Read source file content with error handling."""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        console.print(f"[red]Error: Cannot read {file_path} - invalid encoding[/red]")
        raise
    except Exception as e:
        console.print(f"[red]Error reading file {file_path}: {e}[/red]")
        raise


def build_test_prompt(source_code: str, file_path: Path, language: str) -> str:
    """Build prompt for initial test generation."""
    
    return (
        f"You are an expert test engineer. Generate comprehensive Jest test cases.\n\n"
        f"SOURCE FILE: {file_path.name}\n"
        f"LANGUAGE: {language}\n\n"
        f"SOURCE CODE:\n"
        f"```{language}\n"
        f"{source_code}\n"
        f"```\n\n"
        f"YOUR TASK:\n"
        f"Analyze the source code carefully and generate a complete Jest test file.\n\n"
        f"CRITICAL INSTRUCTIONS:\n\n"
        f"1. IMPORTS (must be at top of file in this exact order):\n"
        f"   - First: Import all needed Jest functions from '@jest/globals'\n"
        f"     Analyze what you need: describe, test, expect, beforeAll, afterAll, beforeEach, afterEach, jest\n"
        f"     Import only what you actually use in the tests\n"
        f"   - Second: Import the module being tested with correct relative path\n"
        f"   - Use ES module syntax (import/export)\n\n"
        f"2. ANALYZE THE SOURCE CODE:\n"
        f"   - Identify all exports (named exports, default exports, CommonJS exports)\n"
        f"   - Determine the correct import statement for the source module\n"
        f"   - Understand each function's purpose, parameters, and return values\n\n"
        f"3. TEST STRUCTURE:\n"
        f"   - Wrap all tests in a top-level describe block with the module name\n"
        f"   - Group related functions in nested describe blocks\n"
        f"   - Each test should have a clear, descriptive name\n\n"
        f"4. TEST COVERAGE - For EVERY exported function:\n"
        f"   - Test normal operation with valid inputs\n"
        f"   - Test edge cases (zero, negative, empty, boundary values)\n"
        f"   - Test error conditions (invalid inputs, exceptions)\n"
        f"   - Test multiple scenarios for complex functions\n\n"
        f"5. BEST PRACTICES:\n"
        f"   - Follow AAA pattern: Arrange, Act, Assert\n"
        f"   - Use appropriate Jest matchers: toBe, toEqual, toStrictEqual, toThrow, toBeCloseTo, etc.\n"
        f"   - Use toThrow() for functions that should throw errors\n"
        f"   - Use toBeCloseTo() for floating-point comparisons\n"
        f"   - One assertion per test when possible\n"
        f"   - No console.log statements in tests\n\n"
        f"6. FORMAT:\n"
        f"   - 2 spaces for indentation\n"
        f"   - Clean, readable code\n"
        f"   - Logical grouping of related tests\n\n"
        f"OUTPUT FORMAT:\n"
        f"- Return ONLY the complete test code\n"
        f"- First line must be the Jest imports\n"
        f"- Second line must be the module import\n"
        f"- Then all test code\n"
        f"- NO markdown code blocks or backticks\n"
        f"- NO explanations or additional text\n"
    )


def build_fix_prompt(source_code: str, test_code: str, errors: str, language: str) -> str:
    """Build prompt for fixing failed tests."""
    
    return (
        f"You are an expert test engineer. Fix the failing Jest tests.\n\n"
        f"SOURCE CODE:\n"
        f"```{language}\n"
        f"{source_code}\n"
        f"```\n\n"
        f"CURRENT TEST CODE:\n"
        f"```{language}\n"
        f"{test_code}\n"
        f"```\n\n"
        f"TEST ERRORS:\n"
        f"```\n"
        f"{errors}\n"
        f"```\n\n"
        f"YOUR TASK - Fix these issues:\n"
        f"1. Check imports are complete and correct:\n"
        f"   - Jest functions imported from '@jest/globals'\n"
        f"   - Module import path is correct\n"
        f"   - All used functions are imported\n"
        f"2. Fix failing tests based on error messages\n"
        f"3. Correct any wrong assertions or matchers\n"
        f"4. Fix function call signatures if wrong\n"
        f"5. Keep ALL passing tests exactly as they are\n"
        f"6. Return the COMPLETE fixed test file with all tests\n\n"
        f"OUTPUT FORMAT:\n"
        f"- Return ONLY the complete fixed test code\n"
        f"- Must include all necessary Jest imports from '@jest/globals'\n"
        f"- NO markdown code blocks or backticks\n"
        f"- NO explanations or additional text\n"
    )


def create_qa_workspace(source_path: Path, input_type: str, language_config: Dict[str, Any]) -> Dict[str, Path]:
    """Create QA agent workspace with proper folder structure based on language config."""
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    workspace_name = f"qa-agent-{timestamp}-{unique_id}"
    
    if input_type == "file":
        workspace_root = source_path.parent / workspace_name
    else:
        workspace_root = source_path / workspace_name
    
    workspace_structure = language_config["workspace_structure"][input_type]
    
    source_dir = workspace_root
    if workspace_structure["source_dir"]:
        source_dir = workspace_root / workspace_structure["source_dir"]
    
    test_dir = workspace_root / workspace_structure["test_dir"]
    
    source_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)
    
    console.print(f"\n[bold green]QA Workspace Created:[/bold green]")
    console.print(f"  [cyan]{workspace_root}[/cyan]")
    
    return {
        "workspace_root": workspace_root,
        "source_dir": source_dir,
        "test_dir": test_dir,
        "mirror_structure": workspace_structure["mirror_structure"],
    }


def copy_source_files(source_path: Path, structure: Dict[str, Path], input_type: str) -> List[Path]:
    """Copy source files to workspace source directory."""
    source_dir = structure["source_dir"]
    copied_files = []
    
    if source_path.is_file():
        dest = source_dir / source_path.name
        shutil.copy2(source_path, dest)
        console.print(f"[green]  Copied: {source_path.name} -> src/[/green]")
        copied_files.append(dest)
    else:
        if structure["mirror_structure"]:
            for item in source_path.rglob("*"):
                if item.is_file() and item.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                    rel_path = item.relative_to(source_path)
                    dest = source_dir / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
                    console.print(f"[green]  Copied: {rel_path} -> src/[/green]")
                    copied_files.append(dest)
        else:
            for item in source_path.rglob("*"):
                if item.is_file() and item.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                    dest = source_dir / item.name
                    shutil.copy2(item, dest)
                    console.print(f"[green]  Copied: {item.name} -> src/[/green]")
                    copied_files.append(dest)
    
    return copied_files


def create_config_files(structure: Dict[str, Path], language_config: Dict[str, Any]) -> None:
    """Create language-specific config files in workspace root."""
    config_files = language_config.get("config_files", {})
    workspace_root = structure["workspace_root"]
    
    for filename, content in config_files.items():
        file_path = workspace_root / filename
        file_path.write_text(content)
        console.print(f"[green]  Created: {filename}[/green]")


def save_test_file(test_code: str, source_file: Path, structure: Dict[str, Path], language_config: Dict[str, Any]) -> Path:
    """Save generated test file in tests directory with proper naming."""
    pattern = language_config["test_file_pattern"]
    test_name = pattern.replace("{name}", source_file.stem)
    test_path = structure["test_dir"] / test_name
    
    test_path.write_text(test_code, encoding="utf-8")
    console.print(f"[green]  Test saved: tests/{test_name}[/green]")
    return test_path


def validate_file(file_path: Path) -> bool:
    """Validate if file is supported and accessible."""
    if not file_path.exists():
        console.print(f"[red]Error: File not found - {file_path}[/red]")
        return False
    
    if not file_path.is_file():
        console.print(f"[red]Error: Not a file - {file_path}[/red]")
        return False
    
    try:
        detect_language(file_path)
        return True
    except ValueError:
        console.print(f"[red]Error: Unsupported file type - {file_path.suffix}[/red]")
        return False


def collect_files(source_path: Path) -> List[Path]:
    """Collect all supported files from source path."""
    if source_path.is_file():
        return [source_path] if validate_file(source_path) else []
    
    supported_files = []
    for ext in [".js", ".jsx", ".ts", ".tsx"]:
        supported_files.extend(source_path.rglob(f"*{ext}"))
    
    return supported_files


def generate_tests_with_llm(
    llm,
    source_code: str,
    file_path: Path,
    language: str,
    test_code: Optional[str] = None,
    errors: Optional[str] = None,
) -> Optional[str]:
    """Generate or fix test code using LLM."""
    try:
        if test_code is None:
            prompt = build_test_prompt(source_code, file_path, language)
        else:
            prompt = build_fix_prompt(source_code, test_code, errors, language)
        
        response = llm.invoke(prompt)
        return clean_test_code(response.content)
    except Exception as e:
        console.print(f"[red]LLM generation failed: {e}[/red]")
        return None


def process_file(
    file_path: Path,
    structure: Dict[str, Path],
    language_config: Dict[str, Any],
) -> Dict[str, Any]:
    """Process single file through test generation and sandbox execution."""
    
    console.print(f"\n[bold cyan]{'='*60}[/bold cyan]")
    console.print(f"[bold cyan]Processing: {file_path.name}[/bold cyan]")
    console.print(f"[bold cyan]{'='*60}[/bold cyan]")
    
    language = detect_language(file_path)
    
    console.print(f"  Language: [yellow]{language_config['name']}[/yellow]")
    console.print(f"  Docker Image: [yellow]{language_config['image']}[/yellow]")
    
    source_code = read_source_file(file_path)
    llm = get_llm()
    sandbox = create_sandbox()
    
    test_code = None
    passed = False
    attempts = 0
    errors = []
    
    console.print("\n[bold]Setting up Docker sandbox...[/bold]")
    
    workspace = sandbox.setup_workspace(
        source_path=file_path,
        input_type="file",
        language_config=language_config,
    )
    
    try:
        sandbox.prepare_workspace(file_path, workspace)
        sandbox.create_config_files(workspace)
        console.print("[green]Sandbox workspace ready[/green]")
        
        while attempts < MAX_RETRIES and not passed:
            attempts += 1
            console.print(f"\n[bold yellow]Attempt {attempts}/{MAX_RETRIES}[/bold yellow]")
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "[cyan]Generating test code via LLM...[/cyan]",
                    total=None
                )
                
                if attempts == 1:
                    test_code = generate_tests_with_llm(
                        llm, source_code, file_path, language
                    )
                else:
                    test_code = generate_tests_with_llm(
                        llm, source_code, file_path, language,
                        test_code=test_code, errors=errors[-1]
                    )
                
                progress.remove_task(task)
            
            if not test_code:
                console.print("[red]Failed to generate test code[/red]")
                continue
            
            test_file_name = language_config["test_file_pattern"].replace(
                "{name}", file_path.stem
            )
            test_file_path = workspace["test_dir"] / test_file_name
            test_file_path.write_text(test_code)
            
            console.print("[bold]Executing tests in Docker sandbox...[/bold]")
            
            try:
                results = sandbox.execute_tests(workspace, timeout=120)
            except Exception as e:
                console.print(f"[red]Sandbox execution error: {e}[/red]")
                errors.append(str(e))
                continue
            
            if results["passed"]:
                passed = True
                console.print(Panel(
                    "[bold green]All tests passed successfully![/bold green]",
                    border_style="green"
                ))
                save_test_file(test_code, file_path, structure, language_config)
            else:
                console.print(Panel(
                    "[bold red]Tests failed[/bold red]",
                    border_style="red"
                ))
                
                if results.get("stderr"):
                    error_msg = results["stderr"][:500]
                    console.print(Panel(
                        error_msg,
                        title="Error Output",
                        border_style="red"
                    ))
                
                errors.append(results.get("stderr", ""))
                
                if attempts >= MAX_RETRIES:
                    console.print("[yellow]Max retries reached[/yellow]")
                    save_test_file(test_code, file_path, structure, language_config)
    
    finally:
        console.print("\n[bold]Cleaning up sandbox...[/bold]")
        sandbox.cleanup(workspace)
        console.print("[green]Sandbox cleaned up successfully[/green]")
    
    return {
        "file": str(file_path),
        "language": language,
        "passed": passed,
        "attempts": attempts,
        "errors": errors,
    }


def display_summary(results: List[Dict[str, Any]], structure: Dict[str, Path]) -> None:
    """Display final processing summary."""
    if not results:
        return
    
    console.print(f"\n[bold]{'='*60}[/bold]")
    console.print("[bold]Test Generation Summary[/bold]")
    console.print(f"[bold]{'='*60}[/bold]")
    
    table = Table(title="Results")
    table.add_column("File", style="cyan", no_wrap=True)
    table.add_column("Language", style="yellow")
    table.add_column("Status", style="bold")
    table.add_column("Attempts", justify="right")
    
    for r in results:
        status = "[green]PASSED[/green]" if r["passed"] else "[red]FAILED[/red]"
        table.add_row(
            Path(r["file"]).name,
            r["language"],
            status,
            str(r["attempts"])
        )
    
    console.print(table)
    
    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    failed_count = total - passed_count
    
    console.print(f"\n[bold]Total Files:[/bold] {total}")
    console.print(f"[bold green]Passed: {passed_count}[/bold green]")
    console.print(f"[bold red]Failed: {failed_count}[/bold red]")
    
    console.print(f"\n[bold green]Workspace: {structure['workspace_root']}[/bold green]")


def handle_file_input() -> None:
    """Handle single file input."""
    source = Prompt.ask("\nEnter file path")
    source_path = Path(source).resolve()
    
    if not validate_file(source_path):
        return
    
    language = detect_language(source_path)
    language_config = get_language_config(language)
    
    console.print(f"\n[bold]Detected Language:[/bold] [yellow]{language_config['name']}[/yellow]")
    
    structure = create_qa_workspace(source_path, "file", language_config)
    
    console.print(f"\n[bold]Creating project structure...[/bold]")
    console.print(f"  [cyan]workspace/[/cyan]")
    console.print(f"  [cyan]├── src/[/cyan]")
    console.print(f"  [cyan]└── tests/[/cyan]")
    
    create_config_files(structure, language_config)
    copied_files = copy_source_files(source_path, structure, "file")
    
    results = []
    for f in copied_files:
        result = process_file(f, structure, language_config)
        results.append(result)
    
    display_summary(results, structure)


def handle_folder_input() -> None:
    """Handle folder input."""
    source = Prompt.ask("\nEnter folder path")
    source_path = Path(source).resolve()
    
    if not source_path.exists():
        console.print(f"[red]Error: Folder not found - {source_path}[/red]")
        return
    
    if not source_path.is_dir():
        console.print(f"[red]Error: Not a directory - {source_path}[/red]")
        return
    
    supported_files = collect_files(source_path)
    
    if not supported_files:
        console.print("[yellow]No supported JavaScript/TypeScript files found[/yellow]")
        return
    
    console.print(f"\n[bold]Found {len(supported_files)} supported file(s):[/bold]")
    for i, f in enumerate(supported_files, 1):
        console.print(f"  {i}. {f.relative_to(source_path)}")
    
    proceed = Confirm.ask("\nProceed with test generation?")
    if not proceed:
        console.print("[yellow]Operation cancelled by user[/yellow]")
        return
    
    language = detect_language(supported_files[0])
    language_config = get_language_config(language)
    
    console.print(f"\n[bold]Detected Language:[/bold] [yellow]{language_config['name']}[/yellow]")
    
    structure = create_qa_workspace(source_path, "folder", language_config)
    
    console.print(f"\n[bold]Creating project structure...[/bold]")
    console.print(f"  [cyan]workspace/[/cyan]")
    console.print(f"  [cyan]├── src/[/cyan]")
    console.print(f"  [cyan]└── tests/[/cyan]")
    
    create_config_files(structure, language_config)
    copied_files = copy_source_files(source_path, structure, "folder")
    
    results = []
    for i, f in enumerate(copied_files, 1):
        console.print(f"\n[bold blue]File {i}/{len(copied_files)}[/bold blue]")
        result = process_file(f, structure, language_config)
        results.append(result)
    
    display_summary(results, structure)


def main():
    """Main entry point with interactive menu."""
    
    console.clear()
    console.print(Panel.fit(
        "[bold cyan]QA Agent - Automated Test Generation[/bold cyan]\n"
        "[yellow]JavaScript & TypeScript Test Generator with Docker Sandbox[/yellow]\n"
        "[dim]Creates isolated workspace with proper src/tests structure[/dim]",
        border_style="cyan",
        padding=(1, 2)
    ))
    
    while True:
        console.print("\n[bold]Select Input Type:[/bold]")
        console.print("  [1] Single File")
        console.print("  [2] Folder")
        console.print("  [3] GitHub Repository (coming soon)")
        console.print("  [4] Exit")
        
        choice = Prompt.ask("\nEnter choice", choices=["1", "2", "3", "4"])
        
        if choice == "1":
            handle_file_input()
        elif choice == "2":
            handle_folder_input()
        elif choice == "3":
            console.print(Panel(
                "[yellow]GitHub repository support is coming soon![/yellow]",
                border_style="yellow"
            ))
        elif choice == "4":
            console.print("\n[bold green]Thank you for using QA Agent![/bold green]")
            sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)