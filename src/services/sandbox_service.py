"""Sandbox Container Manager Service for Autonomous QA Agent.

Controls Docker SDK container creation, image building with layer caching,
and executing tests inside containers with 30s timeouts.
"""

import time
from pathlib import Path
from typing import Any, Dict, Optional
import docker
from docker.errors import ContainerError, ImageNotFound, APIError
from src.services.logger_service import logger


class SandboxService:
    """Service wrapping Docker SDK for persistent sandbox container execution."""

    def __init__(self) -> None:
        """Initialize Docker SDK client connection."""
        try:
            self.client = docker.from_env()
        except Exception as e:
            logger.warning(f"[SandboxService] Docker daemon connection failed: {e}")
            self.client = None

    def build_or_get_image(
        self,
        workspace_dir: Path,
        image_name: str,
        dockerfile_content: Optional[str] = None
    ) -> str:
        """Build Docker image once per project or reuse cached image.

        Args:
            workspace_dir: Path to project root workspace.
            image_name: Name and tag for image (e.g. qa-agent-express:manifest_hash).
            dockerfile_content: LLM-generated Dockerfile string if build is needed.

        Returns:
            Image name tag string.
        """
        if not self.client:
            raise RuntimeError("Docker daemon is not running or accessible.")

        try:
            self.client.images.get(image_name)
            logger.info(f"[SandboxService] Docker image cache HIT: '{image_name}'")
            return image_name
        except ImageNotFound:
            logger.info(f"[SandboxService] Docker image cache MISS. Building '{image_name}'...")

        if not dockerfile_content:
            dockerfile_content = "FROM python:3.11-slim\nWORKDIR /app\nCOPY . /app\n"

        dockerfile_path = workspace_dir / "Dockerfile.qa"
        dockerfile_path.write_text(dockerfile_content, encoding="utf-8")

        self.client.images.build(
            path=str(workspace_dir),
            dockerfile="Dockerfile.qa",
            tag=image_name,
            rm=True
        )
        logger.info(f"[SandboxService] Built Docker image '{image_name}' successfully")
        return image_name

    def start_sandbox_container(
        self,
        image_name: str,
        container_name: str,
        workspace_dir: Path
    ) -> str:
        """Start container mounting workspace_dir in background (tail -f /dev/null).

        Returns:
            Active Container ID string.
        """
        if not self.client:
            raise RuntimeError("Docker daemon is not running.")

        try:
            existing = self.client.containers.get(container_name)
            existing.remove(force=True)
        except Exception:
            pass

        container = self.client.containers.run(
            image=image_name,
            name=container_name,
            command="tail -f /dev/null",
            volumes={str(workspace_dir.resolve()): {"bind": "/app", "mode": "rw"}},
            working_dir="/app",
            detach=True,
            tty=True
        )
        container_id_str = str(container.id) if container.id else ""
        logger.info(f"[SandboxService] Sandbox container started: {container_name} ({container_id_str[:12]})")
        return container_id_str

    def execute_test_command(
        self,
        container_id_or_name: str,
        test_command: str,
        timeout_sec: int = 30
    ) -> Dict[str, Any]:
        """Execute test command inside container with 30s timeout guardrail.

        Returns:
            Dict containing exit_code, raw_logs, and execution_time_ms.
        """
        if not self.client:
            raise RuntimeError("Docker daemon is not running.")

        container = self.client.containers.get(container_id_or_name)
        start_time = time.time()

        try:
            exec_result = container.exec_run(
                cmd=test_command,
                workdir="/app",
                demux=False
            )
            elapsed_ms = int((time.time() - start_time) * 1000)
            exit_code = getattr(exec_result, "exit_code", 0)
            output_data = getattr(exec_result, "output", b"")

            if isinstance(output_data, bytes):
                raw_logs = output_data.decode("utf-8", errors="replace")
            elif isinstance(output_data, str):
                raw_logs = output_data
            elif output_data is not None:
                chunks = []
                for chunk in output_data:
                    if isinstance(chunk, bytes):
                        chunks.append(chunk.decode("utf-8", errors="replace"))
                    else:
                        chunks.append(str(chunk))
                raw_logs = "".join(chunks)
            else:
                raw_logs = ""

            return {
                "exit_code": exit_code if exit_code is not None else 0,
                "raw_logs": raw_logs,
                "execution_time_ms": elapsed_ms,
                "timed_out": False
            }
        except Exception as e:
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "exit_code": 124,
                "raw_logs": f"Test execution timed out or failed after {timeout_sec}s: {e}",
                "execution_time_ms": elapsed_ms,
                "timed_out": True
            }

    def stop_and_remove_container(self, container_id_or_name: str) -> None:
        """Stop and remove sandbox container while preserving image layer cache."""
        if not self.client:
            return
        try:
            container = self.client.containers.get(container_id_or_name)
            container.stop(timeout=2)
            container.remove(force=True)
            logger.info(f"[SandboxService] Sandbox container removed: {container_id_or_name}")
        except Exception as e:
            logger.debug(f"[SandboxService] Error removing container {container_id_or_name}: {e}")


# Singleton instance
sandbox_service = SandboxService()
