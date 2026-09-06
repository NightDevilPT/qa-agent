"""Professional Terminal Logger Service for Auto-Dubber.

Provides structured, colored console output with rich tables, panels,
live status banners, prompt inspection blocks, and quality control evaluation dashboards.
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Initialize global Rich Console
console = Console()

# Define custom SUCCESS log level
SUCCESS_LEVEL_NUM = 25
logging.addLevelName(SUCCESS_LEVEL_NUM, "SUCCESS")


class TerminalColors:
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    
    GRAY = "\033[90m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"


class ColoredFormatter(logging.Formatter):
    """Custom Logging Formatter providing professional colored terminal output."""

    LEVEL_COLOR_MAP = {
        logging.DEBUG: TerminalColors.GRAY,
        logging.INFO: TerminalColors.CYAN,
        SUCCESS_LEVEL_NUM: TerminalColors.GREEN,
        logging.WARNING: TerminalColors.YELLOW,
        logging.ERROR: TerminalColors.RED,
        logging.CRITICAL: TerminalColors.RED + TerminalColors.BOLD,
    }

    LEVEL_TAG_MAP = {
        logging.DEBUG: "DEBUG",
        logging.INFO: "INFO ",
        SUCCESS_LEVEL_NUM: "SUCCESS",
        logging.WARNING: "WARN ",
        logging.ERROR: "ERROR",
        logging.CRITICAL: "CRIT ",
    }

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        color = self.LEVEL_COLOR_MAP.get(record.levelno, TerminalColors.RESET)
        tag = self.LEVEL_TAG_MAP.get(record.levelno, record.levelname)
        module_name = record.name

        message = record.getMessage()

        time_str = f"{TerminalColors.GRAY}[{timestamp}]{TerminalColors.RESET}"
        level_str = f"{color}[{tag}]{TerminalColors.RESET}"
        module_str = f"{TerminalColors.BLUE}[{module_name}]{TerminalColors.RESET}"

        return f"{time_str} {level_str} {module_str} {message}"


class FileFormatter(logging.Formatter):
    """Clean plain-text formatter for log files (no ANSI color codes)."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
        tag = record.levelname
        module_name = record.name
        message = record.getMessage()
        return f"[{timestamp}] [{tag:<7}] [{module_name}] {message}"


class LoggerService:
    """Professional Logger wrapper class supporting rich tables, panels, and dashboards."""

    def __init__(self, name: str = "AutoDubber", log_file: Optional[Union[str, Path]] = None):
        self.name = name
        self._logger = logging.getLogger(name)
        self._logger.setLevel(logging.DEBUG)

        if not self._logger.handlers:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setLevel(logging.INFO)
            console_handler.setFormatter(ColoredFormatter())
            self._logger.addHandler(console_handler)

            if log_file:
                self.attach_file_logger(log_file)

    def attach_file_logger(self, log_file: Union[str, Path]) -> None:
        """Attach a dedicated per-video log file handler inside .temp/[video_name]/logs/."""
        log_path = Path(log_file).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)

        for handler in self._logger.handlers:
            if isinstance(handler, logging.FileHandler) and Path(handler.baseFilename).resolve() == log_path:
                return

        file_handler = logging.FileHandler(str(log_path), encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(FileFormatter())
        self._logger.addHandler(file_handler)

    def info(self, msg: str, *args, **kwargs) -> None:
        """Log an informational message."""
        self._logger.info(msg, *args, **kwargs)

    def success(self, msg: str, *args, **kwargs) -> None:
        """Log an operation success message."""
        self._logger.log(SUCCESS_LEVEL_NUM, msg, *args, **kwargs)

    def warning(self, msg: str, *args, **kwargs) -> None:
        """Log a warning message."""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, msg: str, *args, **kwargs) -> None:
        """Log an error message."""
        self._logger.error(msg, *args, **kwargs)

    def debug(self, msg: str, *args, **kwargs) -> None:
        """Log a debug message."""
        self._logger.debug(msg, *args, **kwargs)

    def step(self, step_num: Any, title: str) -> None:
        """Log a structured pipeline step header banner."""
        step_banner = f"=== STEP {step_num}: {title.upper()} ==="
        panel = Panel(
            Text(step_banner, justify="center", style="bold magenta"),
            border_style="bright_blue",
            expand=True,
        )
        console.print(panel)

    def prompt_inspector(
        self,
        module_name: str,
        system_prompt: str,
        user_prompt: str,
        model_info: str = "LLM Agent",
    ) -> None:
        """Print a structured Prompt Debug Inspector Box in the terminal."""
        table = Table(
            title=f"🔍 PROMPT INSPECTOR [{module_name.upper()}] - Model: {model_info}",
            border_style="magenta",
            show_header=True,
            header_style="bold cyan",
            expand=True,
        )
        table.add_column("Prompt Component", style="bold yellow", width=20)
        table.add_column("Prompt Content", style="white")

        table.add_row("SYSTEM PROMPT", system_prompt)
        table.add_row("USER PROMPT", user_prompt)

        console.print(table)

    def table_summary(
        self,
        title: str,
        items: Dict[str, Any],
        key_header: str = "Property",
        val_header: str = "Value",
        border_style: str = "bright_cyan",
    ) -> None:
        """Print a clean key-value summary table."""
        table = Table(
            title=f"📊 {title.upper()}",
            border_style=border_style,
            show_header=True,
            header_style="bold green",
            expand=True,
        )
        table.add_column(key_header, style="bold cyan", width=25)
        table.add_column(val_header, style="white")

        for key, val in items.items():
            table.add_row(str(key), str(val))

        console.print(table)

    def accuracy_dashboard(
        self,
        lang_name: str,
        score: int,
        passed: bool,
        feedback: str,
        attempt: int,
        max_attempts: int,
    ) -> None:
        """Print the Translation Quality & Accuracy Evaluation Dashboard Table."""
        table = Table(
            title=f"🎯 TRANSLATION QUALITY DASHBOARD - {lang_name.upper()}",
            border_style="yellow" if not passed else "green",
            show_header=True,
            header_style="bold white",
            expand=True,
        )
        table.add_column("Target Language", style="bold cyan", width=18)
        table.add_column("Accuracy Score", style="bold yellow" if score < 85 else "bold green", width=16)
        table.add_column("Evaluation Status", width=22)
        table.add_column("Critic Evaluator Feedback", style="white")

        status_text = (
            f"[bold green]PASSED[/bold green]"
            if passed
            else f"[bold red]FAILED (Attempt {attempt}/{max_attempts})[/bold red]"
        )
        score_display = f"{score}/100"
        feedback_display = feedback if feedback else "Semantic meaning is accurate & natural."

        table.add_row(lang_name, score_display, status_text, feedback_display)
        console.print(table)

    def deliverables_dashboard(self, items: Dict[str, Any]) -> None:
        """Print final deliverable artifacts summary table."""
        table = Table(
            title="🏁 FINAL DELIVERABLE ARTIFACTS DASHBOARD",
            border_style="bright_green",
            show_header=True,
            header_style="bold gold1",
            expand=True,
        )
        table.add_column("Deliverable Artifact", style="bold cyan", width=25)
        table.add_column("Disk Location", style="bright_white")

        for key, val in items.items():
            table.add_row(str(key), str(val))

        console.print(table)

    def token_dashboard(self, token_usage: Dict[str, Dict[str, int]]) -> None:
        """Print LLM Token Usage Metrics per Graph Node in a Rich Table."""
        table = Table(
            title="⚡ LLM TOKEN CONSUMPTION DASHBOARD",
            border_style="bright_blue",
            show_header=True,
            header_style="bold white",
            expand=True,
        )
        table.add_column("LangGraph Node", style="bold cyan", width=25)
        table.add_column("Prompt Tokens", style="bold yellow", justify="right", width=18)
        table.add_column("Completion Tokens", style="bold green", justify="right", width=20)
        table.add_column("Total Tokens", style="bold magenta", justify="right", width=18)

        total_prompt = 0
        total_completion = 0
        total_all = 0

        for node_name, usage in token_usage.items():
            p_tok = usage.get("prompt_tokens", 0)
            c_tok = usage.get("completion_tokens", 0)
            t_tok = usage.get("total_tokens", p_tok + c_tok)

            total_prompt += p_tok
            total_completion += c_tok
            total_all += t_tok

            table.add_row(
                node_name,
                f"{p_tok:,}",
                f"{c_tok:,}",
                f"{t_tok:,}",
            )

        table.add_section()
        table.add_row(
            "[bold white]TOTAL PIPELINE USAGE[/bold white]",
            f"[bold yellow]{total_prompt:,}[/bold yellow]",
            f"[bold green]{total_completion:,}[/bold green]",
            f"[bold magenta]{total_all:,}[/bold magenta]",
        )

        console.print(table)



_active_loggers: Dict[str, LoggerService] = {}
_current_video_log_file: Optional[Path] = None


def configure_video_logger(temp_dir: Union[str, Path]) -> Path:
    """Configure per-video log directory inside .temp/[video_name]/logs/auto_dubber.log."""
    global _current_video_log_file
    temp_path = Path(temp_dir).resolve()
    log_dir = temp_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "auto_dubber.log"
    _current_video_log_file = log_file

    for logger_inst in _active_loggers.values():
        logger_inst.attach_file_logger(log_file)

    return log_file


def get_logger(name: str = "AutoDubber", log_file: Optional[Union[str, Path]] = None) -> LoggerService:
    """Factory helper to obtain a named LoggerService instance."""
    if name in _active_loggers:
        inst = _active_loggers[name]
        if log_file:
            inst.attach_file_logger(log_file)
        elif _current_video_log_file:
            inst.attach_file_logger(_current_video_log_file)
        return inst

    target_file = log_file or _current_video_log_file
    inst = LoggerService(name=name, log_file=target_file)
    _active_loggers[name] = inst
    return inst


# Default global logger instance
logger = get_logger("AutoDubber")
