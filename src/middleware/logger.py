"""
QA Agent Logger Middleware
===========================

Professional logger middleware using LangChain decorator hooks.

Usage:
    from middleware.logger import create_logger_middleware
    
    agent = create_qa_agent(
        middleware=create_logger_middleware(verbose=True)
    )
"""

from typing import Callable
from datetime import datetime
from langchain.agents.middleware import (
    before_agent,
    before_model,
    after_model,
    after_agent,
    wrap_model_call,
    wrap_tool_call,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.tools.tool_node import ToolCallRequest
from langchain.messages import ToolMessage
from langgraph.types import Command
from langgraph.runtime import Runtime
from typing import Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()


def _timestamp() -> str:
    """Get current timestamp."""
    return datetime.now().strftime("%H:%M:%S")


def create_logger_middleware(verbose: bool = False):
    """
    Create professional logger middleware.
    
    Parameters
    ----------
    verbose : bool
        Show detailed output including message content and tool arguments.
    
    Returns
    -------
    list
        List of middleware hooks for create_agent.
    """
    
    counters = {"model": 0, "tool": 0}

    @before_agent
    def log_before_agent(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim")
        table.add_column(style="white")
        
        table.add_row("Time:", _timestamp())
        table.add_row("Phase:", "Agent Initiate")
        table.add_row("Messages:", str(len(state.get("messages", []))))
        
        console.print()
        console.print(Panel(table, border_style="cyan", title="[bold cyan]Agent[/bold cyan]"))
        return None

    @before_model
    def log_before_model(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        counters["model"] += 1
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim", width=10)
        table.add_column(style="white")
        
        table.add_row("Time:", _timestamp())
        table.add_row("Phase:", f"Model Call #{counters['model']}")
        
        if verbose:
            messages = state.get("messages", [])
            if messages:
                last = messages[-1]
                content = last.content if hasattr(last, 'content') else str(last)
                if len(content) > 200:
                    content = content[:200] + "..."
                table.add_row("Input:", content)
        
        console.print()
        console.print(Panel(table, border_style="yellow", title="[bold yellow]Model[/bold yellow]"))
        return None

    @after_model
    def log_after_model(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        messages = state.get("messages", [])
        if not messages:
            return None
            
        last = messages[-1]
        content = last.content if hasattr(last, 'content') else str(last)
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim", width=10)
        table.add_column(style="white")
        
        if hasattr(last, 'tool_calls') and last.tool_calls:
            table.add_row("Tools:", f"{len(last.tool_calls)} call(s)")
            if verbose:
                for tc in last.tool_calls:
                    table.add_row("", f"[bold]{tc.get('name', 'unknown')}[/bold]")
        else:
            if len(content) > 200:
                content = content[:200] + "..."
            table.add_row("Response:", content)
        
        console.print(Panel(table, border_style="green", title="[bold green]Model Done[/bold green]"))
        return None

    @after_agent
    def log_after_agent(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim", width=12)
        table.add_column(style="white")
        
        table.add_row("Time:", _timestamp())
        table.add_row("Phase:", "Agent Complete")
        table.add_row("Model Calls:", str(counters["model"]))
        table.add_row("Tool Calls:", str(counters["tool"]))
        
        console.print()
        console.print(Panel(table, border_style="cyan", title="[bold cyan]Agent Done[/bold cyan]"))
        console.print()
        return None

    @wrap_model_call
    def time_model_call(
        request: ModelRequest,
        handler: Callable[[ModelRequest], ModelResponse],
    ) -> ModelResponse:
        import time
        
        start = time.time()
        try:
            response = handler(request)
            elapsed = time.time() - start
            console.print(f"  [dim]Duration: {elapsed:.2f}s[/dim]")
            return response
        except Exception as e:
            elapsed = time.time() - start
            console.print(f"  [red]Failed: {e} (after {elapsed:.2f}s)[/red]")
            raise

    @wrap_tool_call
    def log_tool_call(
        request: ToolCallRequest,
        handler: Callable[[ToolCallRequest], ToolMessage | Command],
    ) -> ToolMessage | Command:
        counters["tool"] += 1
        tool_name = request.tool_call.get("name", "unknown")
        tool_args = request.tool_call.get("args", {})
        
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column(style="dim", width=10)
        table.add_column(style="white")
        
        table.add_row("Time:", _timestamp())
        table.add_row("Phase:", f"Tool #{counters['tool']}")
        table.add_row("Name:", tool_name)
        
        if verbose and tool_args:
            args_str = str(tool_args)
            if len(args_str) > 200:
                args_str = args_str[:200] + "..."
            table.add_row("Args:", args_str)
        
        console.print()
        console.print(Panel(table, border_style="blue", title="[bold blue]Tool[/bold blue]"))
        
        try:
            result = handler(request)
            console.print(f"  [green]Status: success[/green]")
            
            if verbose and isinstance(result, ToolMessage):
                content = result.content if hasattr(result, 'content') else str(result)
                if len(content) > 200:
                    content = content[:200] + "..."
                console.print(f"  [dim]Result: {content}[/dim]")
            
            console.print(Panel("", border_style="green", title="[bold green]Tool Done[/bold green]"))
            return result
            
        except Exception as e:
            console.print(f"  [red]Status: failed[/red]")
            console.print(f"  [red]Error: {e}[/red]")
            console.print(Panel("", border_style="red", title="[bold red]Tool Failed[/bold red]"))
            raise

    return [
        log_before_agent,
        log_before_model,
        log_after_model,
        log_after_agent,
        time_model_call,
        log_tool_call,
    ]