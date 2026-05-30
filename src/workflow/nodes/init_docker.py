"""
Level 3: Sandbox Initialization Node
Prepares the Docker-mountable workspace using the Sandbox utility.
Starts a persistent background container and runs the initial dependency installation.
"""

from pathlib import Path

from workflow.state import QAState
from utils.logger import get_logger
from constants.languages.config import get_language_config
from utils.sandbox import Sandbox, SandboxError

log = get_logger("init_docker")

def init_docker(state: QAState) -> dict:
    """
    Initializes the Docker workspace, boots a persistent container, 
    runs 'npm install', and stores the container_id in state.
    """
    log.start("init_docker node entered")
    
    target_path_str = state.get("target_path")
    input_type = state.get("input_type")
    project_language = state.get("project_language")
    
    if not target_path_str or not input_type or not project_language:
        log.error("Missing required state keys for Docker init.")
        return {"sandbox_ready": False}
        
    target_path = Path(target_path_str)
    
    if ".temp" not in target_path.parts:
        log.warn("Security Warning: target_path does not appear to be inside the .temp sandbox! Path: %s", target_path)

    lang_config = get_language_config(project_language)
    
    try:
        log.info("Initializing Docker Sandbox environment for %s...", lang_config["name"])
        sandbox = Sandbox()
        
        # 1. Setup the final execution workspace folder structure
        workspace_info = sandbox.setup_workspace(target_path, input_type, lang_config)
        workspace_root = workspace_info["workspace_dir"]
        
        # 2. Populate execution workspace with code and configs
        sandbox.prepare_workspace(target_path, workspace_info)
        sandbox.create_config_files(workspace_info)
        
        # --- NEW: PERSISTENT CONTAINER SETUP ---
        image = lang_config["image"]
        log.info("Pulling/Verifying Docker image: %s", image)
        sandbox._ensure_image(image)  # Reusing the private helper from Sandbox class
        
        log.info("Booting persistent background container...")
        # 'tail -f /dev/null' keeps the container running indefinitely in the background
        container = sandbox.client.containers.run(
            image=image,
            command="tail -f /dev/null", 
            volumes={
                str(workspace_root.absolute()): {
                    "bind": "/workspace",
                    "mode": "rw",
                }
            },
            working_dir="/workspace",
            detach=True,
            network_mode="bridge"  # Required for npm install to reach the internet
        )
        
        # Run the installation command (e.g., 'npm install') inside the container once
        install_cmd = lang_config.get("install_cmd")
        if install_cmd:
            log.info("Running initial setup: %s (This may take a minute...)", install_cmd)
            exit_code, output = container.exec_run(["/bin/sh", "-c", install_cmd])
            
            if exit_code != 0:
                log.error("Installation failed:\n%s", output.decode("utf-8", errors="replace"))
                container.stop()
                container.remove()
                return {"sandbox_ready": False}
            else:
                log.info("Dependencies installed successfully!")
        
        log.end("Persistent container ready! ID: %s", container.id[:12])
        
        # Store the container_id so Level 4 nodes can exec commands into it
        return {
            "workspace_root": str(workspace_root),
            "sandbox_ready": True,
            "container_id": container.id,
        }
        
    except SandboxError as e:
        log.error("Sandbox Initialization Error: %s", e)
        return {"sandbox_ready": False}
    except Exception as e:
        log.error("Unexpected error during Docker init: %s", e)
        return {"sandbox_ready": False}