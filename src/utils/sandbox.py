"""
Docker sandbox utility for isolated test execution.
Handles container lifecycle, workspace setup, and test execution.
"""

import shutil
import tempfile
import pathspec
from pathlib import Path
from typing import Optional, Dict, Any, List
import docker
from docker.errors import DockerException, ImageNotFound, ContainerError
from docker.models.containers import Container

class SandboxError(Exception):
    """Custom exception for sandbox-related errors."""
    pass

class Sandbox:
    """
    Manages Docker containers for isolated test execution.
    """
    
    def __init__(self):
        """Initialize Docker client and verify connection."""
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            raise SandboxError(f"Failed to connect to Docker daemon: {e}")

    def _get_ignore_spec(self, source_dir: Path) -> pathspec.PathSpec:
        """
        Reads .gitignore if present and adds default heavy directories to ignore.
        This prevents copying gigabytes of node_modules into the sandbox.
        """
        ignore_lines = [".git/", "node_modules/", "dist/", "build/", "__pycache__/", ".next/"]
        
        gitignore_path = source_dir / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    ignore_lines.extend(f.readlines())
            except Exception:
                pass # Fail silently if unreadable, stick to defaults
                
        return pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignore_lines)
    
    def setup_workspace(
        self,
        source_path: Path,
        input_type: str,
        language_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create temporary workspace with proper structure inside the local .temp folder."""
        workspace_structure = language_config["workspace_structure"][input_type]
        
        # 1. Find the local .temp folder relative to this file
        # (Assuming this is in src/tools/, we go up three levels to the root)
        project_root = Path(__file__).resolve().parent.parent.parent
        temp_base = project_root / ".temp"
        temp_base.mkdir(exist_ok=True)
        
        # 2. Tell mkdtemp to explicitly create the folder inside our local .temp
        temp_dir = Path(tempfile.mkdtemp(prefix="qa_agent_workspace_", dir=str(temp_base)))

        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        source_dir = workspace_dir
        if workspace_structure["source_dir"]:
            source_dir = workspace_dir / workspace_structure["source_dir"]
        
        test_dir = workspace_dir / workspace_structure["test_dir"]
        
        source_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        return {
            "temp_dir": temp_dir,
            "workspace_dir": workspace_dir,
            "source_dir": source_dir,
            "test_dir": test_dir,
            "mirror_structure": workspace_structure["mirror_structure"],
            "config": language_config,
        }
    
    def prepare_workspace(
        self,
        source_path: Path,
        workspace_info: Dict[str, Any],
    ) -> None:
        """Copy source files to workspace with appropriate structure."""
        source_dir = workspace_info["source_dir"]
        
        if source_path.is_file():
            self._copy_file(source_path, source_dir / source_path.name)
        else:
            spec = self._get_ignore_spec(source_path)
            if workspace_info["mirror_structure"]:
                self._copy_directory_mirrored(source_path, source_dir, spec)
            else:
                self._copy_directory_flat(source_path, source_dir, spec)
    
    def create_config_files(
        self,
        workspace_info: Dict[str, Any],
    ) -> None:
        """Create language-specific configuration files in workspace."""
        config_files = workspace_info["config"].get("config_files", {})
        workspace_dir = workspace_info["workspace_dir"]
        
        for filename, content in config_files.items():
            file_path = workspace_dir / filename
            file_path.write_text(content)
    
    def execute_tests(
        self,
        workspace_info: Dict[str, Any],
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """Execute tests in isolated Docker container."""
        config = workspace_info["config"]
        image = config["image"]
        
        try:
            self._ensure_image(image)
            command = self._build_execution_command(config)
            
            container = self._run_container(
                image=image,
                command=command,
                workspace_dir=workspace_info["workspace_dir"],
                timeout=timeout,
            )
            
            return self._collect_results(container)
            
        except SandboxError:
            raise
        except Exception as e:
            raise SandboxError(f"Test execution failed: {e}")
    
    def cleanup(self, workspace_info: Dict[str, Any]) -> None:
        """Clean up temporary workspace directory."""
        temp_dir = workspace_info["temp_dir"]
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _copy_file(self, source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    
    def _copy_directory_mirrored(self, source_dir: Path, target_dir: Path, spec: pathspec.PathSpec) -> None:
        for item in source_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(source_dir)
                if spec.match_file(str(relative_path)):
                    continue
                
                target_path = target_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_path)
    
    def _copy_directory_flat(self, source_dir: Path, target_dir: Path, spec: pathspec.PathSpec) -> None:
        for item in source_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(source_dir)
                if spec.match_file(str(relative_path)):
                    continue
                shutil.copy2(item, target_dir / item.name)
    
    def _ensure_image(self, image: str) -> None:
        try:
            self.client.images.get(image)
        except ImageNotFound:
            try:
                self.client.images.pull(image)
            except DockerException as e:
                raise SandboxError(f"Failed to pull Docker image '{image}': {e}")
    
    def _build_execution_command(self, config: Dict[str, Any]) -> str:
        commands = []
        if config.get("install_cmd"):
            commands.append(config["install_cmd"])
        if config.get("test_cmd"):
            commands.append(config["test_cmd"])
        return " && ".join(commands)
    
    def _run_container(
        self,
        image: str,
        command: str,
        workspace_dir: Path,
        timeout: int,
    ) -> Container:
        try:
            container = self.client.containers.run(
                image=image,
                command=["/bin/sh", "-c", command],
                volumes={
                    str(workspace_dir.absolute()): {
                        "bind": "/workspace",
                        "mode": "rw",
                    }
                },
                working_dir="/workspace",
                detach=True,
                remove=False,
                mem_limit="1g", # Bumped slightly for npm installs
                network_mode="none" if not command.startswith("npm") else "bridge", # Need bridge to install dependencies
            )
            
            try:
                container.wait(timeout=timeout)
            except Exception:
                container.stop(timeout=5)
                container.remove()
                raise SandboxError(f"Container execution timed out after {timeout}s")
            
            return container
            
        except ContainerError as e:
            raise SandboxError(f"Container error: {e}")
    
    def _collect_results(self, container: Container) -> Dict[str, Any]:
        try:
            container_info = container.attrs
            exit_code = container_info["State"]["ExitCode"]
            
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            try:
                container.remove()
            except DockerException:
                pass
            
            return {
                "passed": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "error": None if exit_code == 0 else stderr or "Tests failed",
            }
        except Exception as e:
            try:
                container.remove()
            except DockerException:
                pass
            raise SandboxError(f"Failed to collect test results: {e}")
            
    def get_supported_files(self, source_path: Path, language_config: Dict[str, Any]) -> List[Path]:
        extensions = tuple(language_config["extensions"])
        
        if source_path.is_file():
            if source_path.suffix in extensions:
                return [source_path]
            return []
            
        spec = self._get_ignore_spec(source_path)
        supported_files = []
        
        for item in source_path.rglob("*"):
            if item.is_file() and item.suffix in extensions:
                relative_path = item.relative_to(source_path)
                # Ensure we don't process tests on node_modules or ignored files
                if not spec.match_file(str(relative_path)):
                    supported_files.append(item)
                    
        return supported_files

def create_sandbox() -> Sandbox:
    return Sandbox()