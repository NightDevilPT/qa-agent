"""Node 3: Universal Ecosystem Profiler & Manifest Discovery Node.

Professional, token-optimized ecosystem detector for FOLDER and GIT_REPO target modes.
Uses LLM structured output with state.json checkpointing via CheckpointService (0 tokens on cache hit)
to extract project language, framework, import system, test framework, logic signatures, and language rules.
"""

import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.llm_provider.factory import LLMProviderFactory
from src.prompts import SYSTEM_ECOSYSTEM_PROMPT, build_detect_ecosystem_user_prompt
from src.services.checkpoint_service import checkpoint_service
from src.services.logger_service import logger
from src.workflow.state import QAState


# --- Structured Pydantic LLM Output Schemas ---

class LogicSignaturesSchema(BaseModel):
    control_flow_keywords: List[str] = Field(
        default_factory=list,
        description="Control flow keywords (e.g. if, elif, else, for, while, try, except, return, raise, switch)"
    )
    async_and_event_signatures: List[str] = Field(
        default_factory=list,
        description="Async and event signatures (e.g. async def, await, Promise, httpx, asyncio, fetch)"
    )
    framework_handler_signatures: List[str] = Field(
        default_factory=list,
        description="Route or handler signatures (e.g. @app.get, @router.post, app.get(, router.get(, req, res)"
    )
    database_query_signatures: List[str] = Field(
        default_factory=list,
        description="Database or ORM query patterns (e.g. SessionLocal, db.query, select(, filter(, mongoose.model, prisma.)"
    )
    negative_non_testable_signatures: List[str] = Field(
        default_factory=list,
        description="Signatures of non-testable files to skip (e.g. __all__ = , settings = , export default config)"
    )


class LanguageRulesSchema(BaseModel):
    non_testable_extensions: List[str] = Field(
        default_factory=list,
        description=(
            "Non-code asset, config, styling, documentation, and build artifact extensions to exclude from testing "
            "(e.g. .png, .css, .json, .md, .env, .d.ts, .map). DO NOT include source code extensions like .js, .ts, .py."
        )
    )
    ignored_directories: List[str] = Field(
        default_factory=list,
        description=(
            "Directories to ignore/exclude from scanning and testing based on project language and framework "
            "(e.g. node_modules, dist, build, .next, __pycache__, .venv, venv, target, vendor, coverage, .git, .vscode, .idea)"
        )
    )
    import_export_patterns: List[str] = Field(
        default_factory=list,
        description=(
            "Regex pattern strings (with capture group 1 capturing module/file paths) matching import/export statements for this programming language."
        )
    )


class EcosystemProfileSchema(BaseModel):
    project_language: str = Field(description="Primary programming language: python, typescript, javascript, go, rust, java, csharp, etc.")
    project_type: str = Field(description="Project type: FRONTEND, BACKEND_API, LIBRARY")
    application_framework: Optional[str] = Field(default=None, description="Web framework name: express, fastapi, react, next, django, flask, gin, nest, or null")
    manifest_file: Optional[str] = Field(default=None, description="Discovered project manifest filename (e.g. package.json, pyproject.toml, go.mod, Cargo.toml, pom.xml, or null)")
    import_system: str = Field(description="Import system: ESM, COMMONJS, PYTHON_RELATIVE, PYTHON_ABSOLUTE, GO_MODULE, RUST_CRATE")
    test_framework: str = Field(description="Test runner: jest, vitest, pytest, unittest, testing, cargo test, etc.")
    test_environment: str = Field(description="Test execution environment: jsdom, node, python, go, rust, java")
    install_command: str = Field(description="Command to install dependencies: npm install, pip install -r requirements.txt, go mod download, etc.")
    logic_signatures: LogicSignaturesSchema
    language_rules: LanguageRulesSchema


# --- Node Main Function ---

def detect_ecosystem_node(state: QAState) -> Dict[str, Any]:
    """Node 3: Dynamic LLM Ecosystem & Manifest Discovery Node for FOLDER & GIT_REPO modes.

    Args:
        state: Active QAState dictionary.

    Returns:
        State update dictionary containing detected ecosystem fields and token consumption updates.
    """
    input_mode = state.get("input_mode", "FOLDER")
    logger.info(f"[Node 3: DetectEcosystem] Profiling project ecosystem (Mode: '{input_mode}')...")

    ws_dir_str = state.get("workspace_dir", "")
    workspace_dir = Path(ws_dir_str).resolve() if ws_dir_str else Path(".temp").resolve()

    # 1. Dynamically inspect top-level workspace files
    root_files: List[str] = []
    if workspace_dir.exists():
        root_files = [p.name for p in workspace_dir.iterdir() if p.is_file() and p.name != "state.json"]

    # Collect dynamic root content snippet for LLM structured inspection
    snippets: List[str] = []
    for f_name in root_files[:8]:
        f_path = workspace_dir / f_name
        try:
            content = f_path.read_text(encoding="utf-8", errors="ignore")[:250]
            snippets.append(f"--- File: {f_name} ---\n{content}")
        except Exception:
            pass
    manifest_snippet = "\n".join(snippets)

    # Compute initial dynamic root structure checksum
    root_hash_input = f"{input_mode}:" + ",".join(sorted(root_files))
    manifest_hash = hashlib.sha256(root_hash_input.encode("utf-8")).hexdigest()

    # 2. Check CheckpointService state.json for cache hit (0 tokens on hit)
    saved_checkpoint = checkpoint_service.load_checkpoint(workspace_dir)
    if saved_checkpoint and saved_checkpoint.get("project_language"):
        logger.success("[Node 3: DetectEcosystem] Checkpoint state.json hit! Reusing profile (0 tokens consumed).")
        return {
            "manifest_hash": saved_checkpoint.get("manifest_hash", manifest_hash),
            "manifest_file": saved_checkpoint.get("manifest_file"),
            "project_language": saved_checkpoint["project_language"],
            "project_type": saved_checkpoint.get("project_type", "BACKEND_API"),
            "application_framework": saved_checkpoint.get("application_framework"),
            "import_system": saved_checkpoint.get("import_system", "ESM"),
            "test_framework": saved_checkpoint.get("test_framework", "pytest"),
            "test_environment": saved_checkpoint.get("test_environment", "python"),
            "install_command": saved_checkpoint.get("install_command", ""),
            "logic_signatures": saved_checkpoint.get("logic_signatures", {}),
            "language_rules": saved_checkpoint.get("language_rules", {}),
        }

    # 3. Single-trigger LLM Profiling Call
    logger.info(f"[Node 3: DetectEcosystem] Invoking LLM profiler for mode '{input_mode}'...")
    provider = LLMProviderFactory.create_provider()

    user_prompt = build_detect_ecosystem_user_prompt(
        input_mode=input_mode,
        root_files=root_files,
        manifest_snippet=manifest_snippet,
    )

    profile_result, usage = provider.generate_structured(
        schema=EcosystemProfileSchema,
        prompt=user_prompt,
        system_prompt=SYSTEM_ECOSYSTEM_PROMPT
    )

    tokens_consumed = usage.get("total_tokens", 0)
    logger.success(f"[Node 3: DetectEcosystem] LLM profiling succeeded ({tokens_consumed} tokens consumed).")

    # If LLM dynamically identified a manifest file, calculate sha256 checksum directly from that file
    if profile_result.manifest_file:
        m_path = workspace_dir / profile_result.manifest_file
        if m_path.exists() and m_path.is_file():
            manifest_hash = hashlib.sha256(m_path.read_bytes()).hexdigest()

    # 4. Construct state payload with global and per-node token tracking
    profile_dict: Dict[str, Any] = {
        "manifest_hash": manifest_hash,
        "manifest_file": profile_result.manifest_file,
        "project_language": profile_result.project_language,
        "project_type": profile_result.project_type,
        "application_framework": profile_result.application_framework,
        "import_system": profile_result.import_system,
        "test_framework": profile_result.test_framework,
        "test_environment": profile_result.test_environment,
        "install_command": profile_result.install_command,
        "logic_signatures": profile_result.logic_signatures.model_dump(),
        "language_rules": profile_result.language_rules.model_dump(),
    }

    # Update global running token count and per-node token map
    current_total_tokens = state.get("total_tokens_used", 0)
    node_tokens = dict(state.get("node_tokens") or {})
    node_tokens["detect_ecosystem_node"] = node_tokens.get("detect_ecosystem_node", 0) + tokens_consumed

    profile_dict["total_tokens_used"] = current_total_tokens + tokens_consumed
    profile_dict["node_tokens"] = node_tokens

    # Persist updated state snapshot to state.json via CheckpointService
    full_updated_state = {**state, **profile_dict}
    checkpoint_service.save_checkpoint(workspace_dir, full_updated_state)

    logger.table_summary(
        title="Ecosystem Detection Confirmed",
        items={
            "Input Mode": input_mode,
            "Language": profile_result.project_language,
            "Project Type": profile_result.project_type,
            "Framework": profile_result.application_framework or "None",
            "Manifest": profile_result.manifest_file or "None",
            "Test Framework": profile_result.test_framework,
            "Install Command": profile_result.install_command,
            "Tokens Used": tokens_consumed,
        }
    )

    return profile_dict
