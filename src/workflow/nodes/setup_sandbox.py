"""
Setup Sandbox Node — Phase 4: Environment Preparation

Uses the Sandbox utility to prepare the Docker environment.
Writes language/framework specific configuration files and installs dependencies
using a node:alpine container.
"""

from pathlib import Path
from typing import Dict, Any

from workflow.state import QAState
from utils.logger import get_logger
from utils.sandbox import create_sandbox, SandboxError
from constants.languages.config import get_language_config

log = get_logger("setup_sandbox")

def setup_sandbox(state: QAState) -> dict:
    """
    LangGraph Node to initialize the Docker sandbox.
    Applies test configurations and runs dependency installation.
    """
    log.start("Setup Sandbox Node — Preparing Docker Environment")

    workspace_root = state.get("workspace_root")
    project_language = state.get("project_language", "javascript")
    project_analysis = state.get("project_analysis", {})

    if not workspace_root:
        log.error("Missing 'workspace_root' in state. Cannot setup sandbox.")
        return {"sandbox_ready": False}

    workspace_path = Path(workspace_root)

    try:
        # 1. Fetch language defaults and Phase 2 analysis configs
        base_lang_config = get_language_config(project_language)
        test_lib_config = project_analysis.get("test_lib_config", {})
        config_files = test_lib_config.get("config_files", {})
        install_packages = test_lib_config.get("install_packages", {})

        # 2. Build the installation command
        # If the project analysis identified specific packages (e.g., jest, types), install them
        if install_packages:
            pkg_strings = [f"{pkg}@{ver}" for pkg, ver in install_packages.items()]
            install_cmd = f"npm install {' '.join(pkg_strings)} --save-dev"
        else:
            # Fallback to a standard install if a package.json already exists
            install_cmd = "npm install"

        # 3. Create the configuration payload for the Sandbox
        docker_config: Dict[str, Any] = {
            **base_lang_config,
            "image": "node:20-alpine",
            "config_files": config_files,
            "install_cmd": install_cmd,
            # test_cmd will be used by the subsequent execute_tests node
            "test_cmd": test_lib_config.get("per_file_test_cmd", "") 
        }

        # Adapt to the Sandbox's expected workspace_info format
        workspace_info = {
            "workspace_dir": workspace_path,
            "source_dir": workspace_path / "src",
            "test_dir": workspace_path / "tests",
            "config": docker_config,
        }

        # 4. Initialize Sandbox and apply configs
        sandbox = create_sandbox()
        
        log.info("Writing configuration files to workspace...")
        sandbox.create_config_files(workspace_info)

        # 5. Run the installation container
        log.info("Pulling image 'node:alpine' and installing dependencies...")
        
        # We temporarily hijack the execute_tests method just to run the install_cmd
        # by creating a copy of workspace_info with NO test_cmd
        install_info = workspace_info.copy()
        install_info["config"] = {**docker_config, "test_cmd": ""}
        
        # Execute the container (Wait up to 5 minutes for npm install)
        result = sandbox.execute_tests(install_info, timeout=300)

        if result["passed"]:
            log.info("Sandbox setup and dependency installation successful.")
            sandbox_ready = True
        else:
            log.error("Sandbox setup failed during installation: %s", result.get("stderr", "Unknown Error"))
            sandbox_ready = False

    except SandboxError as e:
        log.error("Sandbox Docker Error: %s", e)
        sandbox_ready = False
    except Exception as e:
        log.error("Unexpected error during sandbox setup: %s", e)
        sandbox_ready = False

    log.end("Setup sandbox complete")

    return {
        "sandbox_ready": sandbox_ready
    }