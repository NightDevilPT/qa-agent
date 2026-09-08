"""Prompts Package for Autonomous QA Agent."""

from src.prompts.detect_ecosystem_prompt import (
    SYSTEM_ECOSYSTEM_PROMPT,
    build_detect_ecosystem_user_prompt,
)

__all__ = [
    "SYSTEM_ECOSYSTEM_PROMPT",
    "build_detect_ecosystem_user_prompt",
]
