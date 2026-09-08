"""Prompts Package for Autonomous QA Agent."""

from src.prompts.detect_ecosystem_prompt import (
    SYSTEM_ECOSYSTEM_PROMPT,
    build_detect_ecosystem_user_prompt,
)
from src.prompts.setup_docker_prompt import (
    SYSTEM_DOCKER_PROMPT,
    build_setup_docker_user_prompt,
)

__all__ = [
    "SYSTEM_ECOSYSTEM_PROMPT",
    "build_detect_ecosystem_user_prompt",
    "SYSTEM_DOCKER_PROMPT",
    "build_setup_docker_user_prompt",
]

