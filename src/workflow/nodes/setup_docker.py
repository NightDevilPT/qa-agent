"""Node 6: Docker Sandbox Setup & Image Layer Cache Node.

Generates project Dockerfile via LLM ONCE per project on cache miss, or reuses cached Docker image (0 tokens),
spins up persistent sandbox container mounting workspace_dir, and returns container_id, container_name, and image_name.
"""

import re
from pathlib import Path
from typing import Any, Dict

from src.llm_provider.factory import LLMProviderFactory
from src.prompts.setup_docker_prompt import (
    SYSTEM_DOCKER_PROMPT,
    build_setup_docker_user_prompt,
)
from src.services.checkpoint_service import checkpoint_service
from src.services.logger_service import logger
from src.services.sandbox_service import sandbox_service
from src.workflow.state import QAState


def _clean_dockerfile_content(llm_output: str) -> str:
    """Clean markdown code fences or conversational boilerplate from LLM Dockerfile response.

    Args:
        llm_output: Raw text output from LLM provider.

    Returns:
        Clean Dockerfile text string.
    """
    text = llm_output.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:dockerfile|docker)?\n", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\n```$", "", text)
    return text.strip()


def setup_docker_environment_node(state: QAState) -> Dict[str, Any]:
    """Node 6: Setup Docker Sandbox Container & Image Layer Cache.

    Args:
        state: Active QAState dictionary.

    Returns:
        State update payload dictionary containing container_id, container_name, and image_name.
    """
    state = state or {}
    logger.info("[Node 6: SetupDocker] Initializing Docker sandbox container environment...")

    ws_dir_str = state.get("workspace_dir", "")
    workspace_dir = Path(ws_dir_str).resolve() if ws_dir_str else Path(".temp").resolve()
    workspace_dir.mkdir(parents=True, exist_ok=True)

    manifest_hash = state.get("manifest_hash") or "default_hash"
    manifest_file = state.get("manifest_file")
    project_language = state.get("project_language", "generic")
    application_framework = state.get("application_framework")
    test_framework = state.get("test_framework", "pytest")
    test_environment = state.get("test_environment", "node")
    install_command = state.get("install_command", "")
    run_id = state.get("run_id", "sandbox_run")

    folder_name = workspace_dir.name if workspace_dir.name else "app"
    folder_slug = re.sub(r"[^\w]+", "-", folder_name.lower()).strip("-") or "app"
    image_tag = manifest_hash[:12]
    image_name = f"qa-agent-{folder_slug}:{image_tag}".lower()
    container_name = f"qa-agent-container-{run_id}".lower()

    # 1. Check CheckpointService state.json for active running container
    saved_checkpoint = checkpoint_service.load_checkpoint(workspace_dir)
    if (
        saved_checkpoint
        and saved_checkpoint.get("container_id")
        and saved_checkpoint.get("container_id") != "local_sandbox"
    ):
        cid = saved_checkpoint["container_id"]
        if sandbox_service.client:
            try:
                container_obj = sandbox_service.client.containers.get(cid)
                if container_obj.status == "running":
                    logger.success(f"[Node 6: SetupDocker] Container state active & running ({cid[:12]}).")
                    return {
                        "container_id": cid,
                        "container_name": saved_checkpoint.get("container_name", container_name),
                        "image_name": saved_checkpoint.get("image_name", image_name),
                    }
            except Exception:
                pass  # Container stopped or removed outside, recreate container

    tokens_consumed = 0
    image_cached = False

    # Create minimal .dockerignore to keep docker build context transfer fast (<100ms)
    dockerignore_path = workspace_dir / ".dockerignore"
    if not dockerignore_path.exists():
        try:
            dockerignore_path.write_text(
                "node_modules\n.git\n.temp\n__pycache__\n.venv\ndist\nbuild\ncoverage\n.idea\n.vscode\n",
                encoding="utf-8"
            )
        except Exception:
            pass

    # Check local Docker daemon image cache (0 tokens on hit)
    if sandbox_service.client:
        try:
            sandbox_service.client.images.get(image_name)
            image_cached = True
            logger.success(f"[Node 6: SetupDocker] Docker image cache HIT: '{image_name}' (0 LLM tokens).")
        except Exception:
            logger.info(f"[Node 6: SetupDocker] Docker image cache MISS for '{image_name}'. Generating Dockerfile via LLM...")

    # On Cache MISS, generate Dockerfile via LLM ONCE per project
    if not image_cached:
        manifest_snippet = ""
        if manifest_file:
            m_path = workspace_dir / manifest_file
            if m_path.exists() and m_path.is_file():
                try:
                    manifest_snippet = m_path.read_text(encoding="utf-8", errors="ignore")[:300]
                except Exception:
                    pass

        user_prompt = build_setup_docker_user_prompt(
            project_language=project_language,
            application_framework=application_framework,
            test_framework=test_framework,
            test_environment=test_environment,
            install_command=install_command,
            manifest_file=manifest_file,
            manifest_content_snippet=manifest_snippet,
        )

        provider = LLMProviderFactory.create_provider()
        gen_result = provider.generate_with_usage(
            prompt=user_prompt,
            system_prompt=SYSTEM_DOCKER_PROMPT,
        )

        response_text = gen_result.get("content", "")
        tokens_consumed = gen_result.get("total_tokens", 0)
        dockerfile_content = _clean_dockerfile_content(response_text)
        logger.success(f"[Node 6: SetupDocker] LLM generated Dockerfile ONCE ({tokens_consumed} tokens).")

        # Build & tag image using SandboxService
        sandbox_service.build_or_get_image(
            workspace_dir=workspace_dir,
            image_name=image_name,
            dockerfile_content=dockerfile_content,
        )

    # Start/reuse persistent sandbox container
    container_id = sandbox_service.start_sandbox_container(
        image_name=image_name,
        container_name=container_name,
        workspace_dir=workspace_dir,
    )

    # Update global token tracking
    current_total_tokens = state.get("total_tokens_used", 0)
    node_tokens = dict(state.get("node_tokens") or {})
    node_tokens["setup_docker_environment_node"] = node_tokens.get("setup_docker_environment_node", 0) + tokens_consumed

    update_payload: Dict[str, Any] = {
        "container_id": container_id,
        "container_name": container_name,
        "image_name": image_name,
        "total_tokens_used": current_total_tokens + tokens_consumed,
        "node_tokens": node_tokens,
    }

    # Persist updated state snapshot to state.json via CheckpointService
    full_updated_state = {**state, **update_payload}
    checkpoint_service.save_checkpoint(workspace_dir, full_updated_state)

    logger.table_summary(
        title="Docker Sandbox Container Operational",
        items={
            "Container ID": container_id[:12] if container_id else "N/A",
            "Container Name": container_name,
            "Image Tag": image_name,
            "Cache Hit": "YES (0 tokens)" if image_cached else "NO (Built via LLM)",
            "Tokens Used": tokens_consumed,
        }
    )

    return update_payload
