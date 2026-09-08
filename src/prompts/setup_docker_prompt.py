"""Docker Sandbox LLM Prompt Templates.

Defines prompt templates for Node 6 LLM Dockerfile generation ONCE per project.
"""

from typing import Optional

SYSTEM_DOCKER_PROMPT = (
    "You are a DevOps Expert generating a minimal, clean Dockerfile for unit test execution.\n"
    "Output ONLY valid Dockerfile instructions without markdown syntax blocks or conversational commentary.\n"
    "RULES:\n"
    "1. Use official slim base images (e.g. node:20-slim, python:3.11-slim, golang:1.21-alpine, rust:1.75-slim).\n"
    "2. Set WORKDIR /app.\n"
    "3. Copy project files using 'COPY . .'. Do NOT copy specific individual file names unless specified.\n"
    "4. If Install Command is provided, execute it with RUN (e.g. RUN npm install --ignore-scripts || true).\n"
    "5. Do NOT set a CMD or ENTRYPOINT that terminates immediately."
)



def build_setup_docker_user_prompt(
    project_language: str,
    application_framework: Optional[str],
    test_framework: str,
    test_environment: str,
    install_command: str,
    manifest_file: Optional[str],
    manifest_content_snippet: str = "",
) -> str:
    """Build concise user prompt for Dockerfile generation.

    Args:
        project_language: Primary project language (e.g., TypeScript, Python).
        application_framework: Discovered framework (e.g., React, Express).
        test_framework: Test runner (e.g., Jest, Pytest).
        test_environment: Test execution environment (e.g., Node.js, Python).
        install_command: Install command string (e.g., npm install).
        manifest_file: Manifest filename (e.g., package.json).
        manifest_content_snippet: Truncated content of manifest file.

    Returns:
        Formatted user prompt string.
    """
    return (
        f"Language: {project_language}\n"
        f"Framework: {application_framework or 'None'}\n"
        f"Test Runner: {test_framework}\n"
        f"Execution Env: {test_environment}\n"
        f"Manifest File: {manifest_file or 'None'}\n"
        f"Install Command: {install_command or 'None'}\n"
        f"Manifest Snippet:\n{manifest_content_snippet[:300]}\n\n"
        f"Generate Dockerfile."
    )
