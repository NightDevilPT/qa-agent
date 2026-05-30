"""
Level 1: File Discovery Node
Scans the target directory for valid test candidates based on language config.
Isolates local files/folders into a safe `.temp` workspace before extracting.
"""

import os
import shutil
import tempfile
from pathlib import Path
import pathspec

from workflow.state import QAState
from utils.logger import get_logger
from constants.languages.config import (
    get_extensions_for_language,
    get_all_exclude_patterns
)

# Rulebook §2: Use get_logger, no bare print() statements
log = get_logger("extract_files")

def extract_files(state: QAState) -> dict:
    """
    Scan the target project path and extract all valid source files.
    """
    log.start("extract_files node entered")
    
    target_path_str = state.get("target_path")
    input_type = state.get("input_type")
    project_language = state.get("project_language")
    
    # Failsafe check
    if not target_path_str or not input_type or not project_language:
        log.error("Missing required state keys (target_path, input_type, project_language)")
        return {"discovered_files": [], "unplanned_files": []}

    # Safety check for remote URLs (clone_repo node should handle this, but just in case)
    if str(target_path_str).startswith(("http://", "https://", "git@")):
        log.error("Expected a local path but got a remote URL. clone_repo node missed this.")
        return {"discovered_files": [], "unplanned_files": []}

    target_path = Path(target_path_str).resolve()
    
    # --- NEW: Safe Sandbox Workspace Preparation ---
    # If the input is a local file or folder, copy it into our managed .temp directory.
    # (If input_type is 'repo', clone_repo already put it in .temp, so we skip copying)
    if input_type in ["file", "folder"] and ".temp" not in target_path.parts:
        project_root = Path(__file__).resolve().parent.parent.parent.parent
        temp_base = project_root / ".temp"
        temp_base.mkdir(exist_ok=True)
        
        temp_dir = tempfile.mkdtemp(prefix=f"qa_agent_{input_type}_", dir=str(temp_base))
        new_target_dir = Path(temp_dir).resolve()
        
        try:
            if input_type == "folder":
                log.info("Isolating local folder into sandbox workspace: %s", new_target_dir)
                # dirs_exist_ok=True is required because mkdtemp already created the empty folder
                shutil.copytree(target_path, new_target_dir, dirs_exist_ok=True)
                target_path = new_target_dir
                
            elif input_type == "file":
                log.info("Isolating local file into sandbox workspace: %s", new_target_dir)
                copied_file = new_target_dir / target_path.name
                shutil.copy2(target_path, copied_file)
                target_path = copied_file
                
        except Exception as e:
            log.error("Failed to copy %s to sandbox workspace: %s", input_type, e)
            return {"discovered_files": [], "unplanned_files": []}
    # -----------------------------------------------

    log.info("Scanning target path: %s (Language: %s, Mode: %s)", target_path, project_language, input_type)

    # 1. Retrieve language configurations dynamically (Rulebook §8)
    valid_extensions = set(get_extensions_for_language(project_language))
    default_excludes = get_all_exclude_patterns()
    
    discovered_files = []

    # 2. Handle single file input
    if input_type == "file":
        if target_path.is_file() and target_path.suffix.lower() in valid_extensions:
            # We store project-relative paths to make Docker mounting easier later
            discovered_files.append(target_path.name)
        else:
            log.warn("Target is a file but does not match valid extensions: %s", target_path.suffix)
    
    # 3. Handle folder / repo input
    elif input_type in ["folder", "repo"]:
        ignore_lines = list(default_excludes)
        
        # Merge project .gitignore if it exists
        gitignore_path = target_path / ".gitignore"
        if gitignore_path.exists():
            try:
                with open(gitignore_path, "r", encoding="utf-8") as f:
                    ignore_lines.extend(f.readlines())
                log.info("Loaded .gitignore rules")
            except Exception as e:
                log.warn("Failed to read .gitignore: %s", e)
        
        # Compile pathspec
        spec = pathspec.PathSpec.from_lines(pathspec.patterns.GitWildMatchPattern, ignore_lines)
        
        # Traverse the directory tree
        for root, dirs, files in os.walk(target_path):
            root_path = Path(root)
            
            # Optimization: modify `dirs` in-place so os.walk ignores heavy excluded folders completely (e.g. node_modules/)
            dirs[:] = [
                d for d in dirs 
                if not spec.match_file(str((root_path / d).relative_to(target_path)) + "/")
            ]

            for file in files:
                file_path = root_path / file
                
                # Fast check: skip invalid extensions
                if file_path.suffix.lower() not in valid_extensions:
                    continue
                    
                rel_path = file_path.relative_to(target_path)
                
                # Final check: does the file match an exclude pattern?
                if spec.match_file(str(rel_path)):
                    continue
                    
                # Always use forward slashes for internal consistency/Docker compatibility
                discovered_files.append(str(rel_path).replace("\\", "/"))
    else:
        log.error("Unknown input_type provided: %s", input_type)

    log.end("Extraction complete. Found %d testable files.", len(discovered_files))
    
    # Return strictly the keys to update in LangGraph state
    return {
        "target_path": str(target_path),  # <--- CRITICAL: Push the new safe sandbox path to state
        "discovered_files": discovered_files,
        "unplanned_files": discovered_files.copy()  # Initialize the queue for Level 2 loop
    }