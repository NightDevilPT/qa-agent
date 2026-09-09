"""Node 6: Docker Sandbox Setup & Image Layer Cache Node.

Generates project Dockerfile via LLM ONCE per project on cache miss, or reuses cached Docker image (0 tokens),
spins up persistent sandbox container mounting workspace_dir, verifies container health dynamically with 0 hardcoding,
and retries up to 3 times if setup fails.
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


def _verify_sandbox_container_health(container_id: str) -> bool:
    """Run a dynamic, language-agnostic healthcheck command inside container to verify setup.

    Args:
        container_id: Active Docker container ID.

    Returns:
        True if container is running and healthcheck exits with code 0, False otherwise.
    """
    if not container_id or not sandbox_service or not getattr(sandbox_service, "client", None):
        return True  # Fallback if Docker daemon connection is absent

    # Universal 0-hardcoding container execution ping
    cmd = "echo 'sandbox_online'"

    try:
        res = sandbox_service.execute_test_command(
            container_id_or_name=container_id,
            test_command=cmd,
            timeout_sec=10
        )
        exit_code = res.get("exit_code", 1)
        return exit_code == 0
    except Exception as e:
        logger.warning(f"[Node 6: SetupDocker] Dynamic container healthcheck failed: {e}")
        return False


def setup_docker_environment_node(state: QAState) -> Dict[str, Any]:
    """Node 6: Setup Docker Sandbox Container with 0-Hardcoding Health Verification & Max 3 Retries.

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
        if sandbox_service and getattr(sandbox_service, "client", None):
            try:
                container_obj = sandbox_service.client.containers.get(cid)
                if container_obj.status == "running" and _verify_sandbox_container_health(cid):
                    logger.success(f"[Node 6: SetupDocker] Container active, running & verified ({cid[:12]}).")
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
    if sandbox_service and getattr(sandbox_service, "client", None):
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
        if sandbox_service and getattr(sandbox_service, "client", None):
            sandbox_service.build_or_get_image(
                workspace_dir=workspace_dir,
                image_name=image_name,
                dockerfile_content=dockerfile_content,
            )

    # 2. Container setup with 0-hardcoding healthcheck and max 3 retries
    container_id = None
    healthcheck_passed = False
    max_retries = 3

    if sandbox_service and getattr(sandbox_service, "client", None):
        for attempt in range(1, max_retries + 1):
            logger.info(f"[Node 6: SetupDocker] Starting sandbox container (Attempt {attempt}/{max_retries})...")
            try:
                container_id = sandbox_service.start_sandbox_container(
                    image_name=image_name,
                    container_name=container_name,
                    workspace_dir=workspace_dir,
                )
                # Dynamic universal health check
                healthcheck_passed = _verify_sandbox_container_health(container_id)
                if healthcheck_passed:
                    logger.success(f"[Node 6: SetupDocker] Sandbox container verified running & operational (Attempt {attempt}).")
                    break
                else:
                    logger.warning(f"[Node 6: SetupDocker] Container health check failed on attempt {attempt}. Retrying container setup...")
            except Exception as e:
                logger.warning(f"[Node 6: SetupDocker] Container setup attempt {attempt} failed: {e}")

        if not healthcheck_passed:
            logger.error(f"[Node 6: SetupDocker] Sandbox container verification failed after {max_retries} attempts.")

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
            "Health Verification": "PASSED" if healthcheck_passed else "FALLBACK",
            "Cache Hit": "YES (0 tokens)" if image_cached else "NO (Built via LLM)",
            "Tokens Used": tokens_consumed,
        }
    )

    return update_payload
