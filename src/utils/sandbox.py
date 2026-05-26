"""
Docker sandbox utility for isolated test execution.
Handles container lifecycle, workspace setup, and test execution.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any
import docker
from docker.errors import DockerException, ImageNotFound, ContainerError
from docker.models.containers import Container


class SandboxError(Exception):
    """Custom exception for sandbox-related errors."""
    pass


class Sandbox:
    """
    Manages Docker containers for isolated test execution.
    
    Responsibilities:
    - Create isolated workspace directories
    - Copy source files with proper structure
    - Run tests in language-specific Docker containers
    - Clean up resources after execution
    """
    
    def __init__(self):
        """Initialize Docker client and verify connection."""
        try:
            self.client = docker.from_env()
            self.client.ping()
        except DockerException as e:
            raise SandboxError(f"Failed to connect to Docker daemon: {e}")
    
    def setup_workspace(
        self,
        source_path: Path,
        input_type: str,
        language_config: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Create temporary workspace with proper structure.
        
        Args:
            source_path: Path to source file or directory
            input_type: Type of input ('file', 'folder', or 'repo')
            language_config: Language configuration from constants
            
        Returns:
            Dictionary with workspace paths and configuration
        """
        workspace_structure = language_config["workspace_structure"][input_type]
        
        # Create temporary workspace
        temp_dir = Path(tempfile.mkdtemp(prefix="qa_agent_"))
        workspace_dir = temp_dir / "workspace"
        workspace_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine source and test directories
        source_dir = workspace_dir
        if workspace_structure["source_dir"]:
            source_dir = workspace_dir / workspace_structure["source_dir"]
        
        test_dir = workspace_dir / workspace_structure["test_dir"]
        
        # Create directories
        source_dir.mkdir(parents=True, exist_ok=True)
        test_dir.mkdir(parents=True, exist_ok=True)
        
        workspace_info = {
            "temp_dir": temp_dir,
            "workspace_dir": workspace_dir,
            "source_dir": source_dir,
            "test_dir": test_dir,
            "mirror_structure": workspace_structure["mirror_structure"],
            "config": language_config,
        }
        
        return workspace_info
    
    def prepare_workspace(
        self,
        source_path: Path,
        workspace_info: Dict[str, Any],
    ) -> None:
        """
        Copy source files to workspace with appropriate structure.
        
        Args:
            source_path: Original source path
            workspace_info: Workspace information from setup_workspace()
        """
        source_dir = workspace_info["source_dir"]
        
        if source_path.is_file():
            # Handle single file
            self._copy_file(source_path, source_dir / source_path.name)
        else:
            # Handle directory
            if workspace_info["mirror_structure"]:
                self._copy_directory_mirrored(source_path, source_dir)
            else:
                self._copy_directory_flat(source_path, source_dir)
    
    def create_config_files(
        self,
        workspace_info: Dict[str, Any],
    ) -> None:
        """
        Create language-specific configuration files in workspace.
        
        Args:
            workspace_info: Workspace information from setup_workspace()
        """
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
        """
        Execute tests in isolated Docker container.
        
        Args:
            workspace_info: Workspace information from setup_workspace()
            timeout: Maximum execution time in seconds
            
        Returns:
            Dictionary with test execution results
        """
        config = workspace_info["config"]
        image = config["image"]
        
        try:
            # Ensure image is available
            self._ensure_image(image)
            
            # Build execution command
            command = self._build_execution_command(config)
            
            # Run container
            container = self._run_container(
                image=image,
                command=command,
                workspace_dir=workspace_info["workspace_dir"],
                timeout=timeout,
            )
            
            # Collect results
            result = self._collect_results(container)
            
            return result
            
        except SandboxError:
            raise
        except Exception as e:
            raise SandboxError(f"Test execution failed: {e}")
    
    def cleanup(self, workspace_info: Dict[str, Any]) -> None:
        """
        Clean up temporary workspace directory.
        
        Args:
            workspace_info: Workspace information from setup_workspace()
        """
        temp_dir = workspace_info["temp_dir"]
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _copy_file(self, source: Path, destination: Path) -> None:
        """Copy a single file to destination."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
    
    def _copy_directory_mirrored(
        self,
        source_dir: Path,
        target_dir: Path,
    ) -> None:
        """Copy directory preserving structure."""
        for item in source_dir.rglob("*"):
            if item.is_file():
                relative_path = item.relative_to(source_dir)
                target_path = target_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, target_path)
    
    def _copy_directory_flat(
        self,
        source_dir: Path,
        target_dir: Path,
    ) -> None:
        """Copy all files to target directory without structure."""
        for item in source_dir.rglob("*"):
            if item.is_file():
                shutil.copy2(item, target_dir / item.name)
    
    def _ensure_image(self, image: str) -> None:
        """
        Ensure Docker image is available locally.
        
        Args:
            image: Docker image name and tag
        """
        try:
            self.client.images.get(image)
        except ImageNotFound:
            try:
                self.client.images.pull(image)
            except DockerException as e:
                raise SandboxError(f"Failed to pull Docker image '{image}': {e}")
    
    def _build_execution_command(self, config: Dict[str, Any]) -> str:
        """
        Build shell command for container execution.
        
        Args:
            config: Language configuration
            
        Returns:
            Shell command string
        """
        commands = []
        
        # Install dependencies
        if config.get("install_cmd"):
            commands.append(config["install_cmd"])
        
        # Run tests
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
        """
        Run Docker container for test execution.
        
        Args:
            image: Docker image to use
            command: Command to execute
            workspace_dir: Directory to mount as workspace
            timeout: Execution timeout
            
        Returns:
            Docker container object
        """
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
                mem_limit="512m",
                cpu_period=100000,
                cpu_quota=50000,
                network_mode="none",  # Isolated network for security
            )
            
            # Wait for completion
            try:
                container.wait(timeout=timeout)
            except Exception as e:
                container.stop(timeout=5)
                container.remove()
                raise SandboxError(f"Container execution timed out after {timeout}s")
            
            return container
            
        except ContainerError as e:
            raise SandboxError(f"Container error: {e}")
    
    def _collect_results(self, container: Container) -> Dict[str, Any]:
        """
        Collect execution results from container.
        
        Args:
            container: Docker container object
            
        Returns:
            Dictionary with execution results
        """
        try:
            # Get container state
            container_info = container.attrs
            exit_code = container_info["State"]["ExitCode"]
            
            # Get logs
            stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
            stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
            
            # Clean up container
            try:
                container.remove()
            except DockerException:
                pass  # Container might already be removed
            
            return {
                "passed": exit_code == 0,
                "exit_code": exit_code,
                "stdout": stdout,
                "stderr": stderr,
                "error": None if exit_code == 0 else stderr or "Tests failed",
            }
            
        except Exception as e:
            # Ensure container is removed even if collection fails
            try:
                container.remove()
            except DockerException:
                pass
            
            raise SandboxError(f"Failed to collect test results: {e}")
    
    def validate_source(self, source_path: Path) -> bool:
        """
        Validate that source path exists and is accessible.
        
        Args:
            source_path: Path to validate
            
        Returns:
            True if valid, False otherwise
        """
        return source_path.exists()
    
    def get_supported_files(
        self,
        source_path: Path,
        language_config: Dict[str, Any],
    ) -> list:
        """
        Get list of supported source files from directory.
        
        Args:
            source_path: Source directory or file
            language_config: Language configuration
            
        Returns:
            List of supported file paths
        """
        extensions = tuple(language_config["extensions"])
        
        if source_path.is_file():
            if source_path.suffix in extensions:
                return [source_path]
            return []
        
        # Collect all matching files
        supported_files = []
        for ext in extensions:
            supported_files.extend(source_path.rglob(f"*{ext}"))
        
        return supported_files


def create_sandbox() -> Sandbox:
    """
    Factory function to create Sandbox instance.
    
    Returns:
        Configured Sandbox instance
    """
    return Sandbox()