"""
Teardown Node — Phase 6: Finalization
Safely shuts down and removes the Docker container/sandbox environment.
"""

from workflow.state import QAState
from utils.logger import get_logger
from utils.sandbox import create_sandbox

log = get_logger("teardown")

def teardown(state: QAState) -> dict:
    log.start("Teardown Node — Cleaning up Docker Sandbox")

    container_id = state.get("container_id")
    
    if container_id:
        try:
            sandbox = create_sandbox()
            
            # Note: Adjust 'cleanup_container' to match the actual teardown 
            # method defined in your utils/sandbox.py
            sandbox.cleanup_container(container_id) 
            
            log.info("Successfully shut down and removed Docker container: %s", container_id)
        except Exception as e:
            log.error("Failed to remove Docker container %s: %s", container_id, e)
    else:
        log.info("No active Docker container ID found in state. Nothing to clean up.")

    log.end("Teardown complete")

    return {
        "container_id": None,
        "sandbox_ready": False
    }