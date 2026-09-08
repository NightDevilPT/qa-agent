# Autonomous QA Agent - System Architecture & Rulebook (`docs/RULES.md`)

This document defines the formal coding conventions, module organization standards, detailed service interface index, and node registration protocols for the **Autonomous QA Agent**.

---

## 1. Core Architecture & Folder Placement Rules

1. **Services Placement (`src/services/`)**:
   * All business services MUST be placed directly in `src/services/` as flat Python modules (e.g., `ast_service.py`, `sandbox_service.py`, `checkpoint_service.py`, `terminal_service.py`, `logger_service.py`).
   * Do NOT create subdirectories inside `src/services/`.
   * Export all service classes and singleton instances in `src/services/__init__.py`.

2. **LLM Provider System (`src/llm_provider/`)**:
   * Any new LLM provider MUST be added in `src/llm_provider/providers/` (e.g. `anthropic_provider.py`, `cohere_provider.py`).
   * Concrete providers MUST inherit from `BaseLLMProvider` in `src/llm_provider/providers/base_provider.py`.
   * Register new providers in `LLMProviderFactory` (`src/llm_provider/factory.py`).

3. **Prompts Placement (`src/prompts/`)**:
   * All LLM system prompts, prompt templates, and user prompt builder functions MUST be placed inside `src/prompts/` (e.g. `detect_ecosystem_prompt.py`, `generate_test_prompt.py`).
   * Hardcoding inline prompt text inside node implementation files is strictly prohibited.
   * Export prompt constants and builder functions in `src/prompts/__init__.py`.

4. **Utilities Placement (`src/utils/`)**:
   * Any general helper utilities (e.g. path helpers, string formatters, hash calculators) MUST be placed inside `src/utils/`.

5. **Workflow & State Machine (`src/workflow/`)**:
   * LangGraph state schema MUST be defined in `src/workflow/state.py` using Python `TypedDict`.
   * StateGraph initialization and routing logic MUST be defined in `src/workflow/graph.py`.
   * LangGraph node implementations MUST be placed in `src/workflow/nodes/`.

6. **Import & Type Safety Rules**:
   * Use absolute package imports (`from src.services.logger_service import logger`).
   * Configure `[tool.pyright]` in `pyproject.toml` with `extraPaths = ["."]` to ensure Pyright / IDE type checkers resolve imports from project root `.`.
   * Enforce strict type annotations and explicit non-null checks (e.g., `str(container.id) if container.id else ""`).

---

## 2. Complete Service Function Signatures & Interface Index

### 🖥️ Service 1: Interactive Terminal Service
* **File Path**: `src/services/terminal_service.py`
* **Class**: `TerminalService` (Singleton: `terminal_service`)
* **Description**: Wraps interactive terminal prompts, single/multi-option selection menus, file path validation, confirmation dialogs, and styled CLI summary boxes.

#### `display_header`
* **Full Signature**:
  ```python
  def display_header(self, title: str, subtitle: Optional[str] = None) -> None
  ```
* **Inputs**:
  - `title` (`str`): Main header title string (e.g., `"AUTONOMOUS QA AGENT SYSTEM"`).
  - `subtitle` (`Optional[str]`): Optional subtitle or description string.
* **Outputs**: `None`
* **Description**: Displays a styled ANSI banner box with border lines in the terminal console.

#### `prompt_file_path`
* **Full Signature**:
  ```python
  def prompt_file_path(
      self,
      prompt_msg: str = "Enter file path",
      default: Optional[str] = None,
      must_exist: bool = True
  ) -> Path
  ```
* **Inputs**:
  - `prompt_msg` (`str`): Label message displayed to the user.
  - `default` (`Optional[str]`): Default path string if user presses Enter.
  - `must_exist` (`bool`): If `True`, repeatedly prompts until an existing disk path is provided.
* **Outputs**: `Path` (Resolved absolute `Path` object).
* **Description**: Prompts user for a file/folder path with string cleaning and existence validation.

#### `prompt_select`
* **Full Signature**:
  ```python
  def prompt_select(
      self,
      prompt_msg: str,
      options: List[Dict[str, str]],
      default_index: int = 0
  ) -> Dict[str, str]
  ```
* **Inputs**:
  - `prompt_msg` (`str`): Prompt label title.
  - `options` (`List[Dict[str, str]]`): Option list containing dictionaries formatted as `{"name": str, "code": str}`.
  - `default_index` (`int`): Default selected option index (0-based).
* **Outputs**: `Dict[str, str]` (The selected option dictionary `{"name": str, "code": str}`).
* **Description**: Renders a numbered selection menu in the CLI and parses user choice.

#### `prompt_multi_select`
* **Full Signature**:
  ```python
  def prompt_multi_select(
      self,
      prompt_msg: str,
      options: List[Dict[str, str]]
  ) -> List[Dict[str, str]]
  ```
* **Inputs**:
  - `prompt_msg` (`str`): Prompt label.
  - `options` (`List[Dict[str, str]]`): Available option dictionaries.
* **Outputs**: `List[Dict[str, str]]` (List of user-selected option dictionaries).
* **Description**: Displays a multi-selection checklist enabling comma-separated choices.

#### `prompt_text`
* **Full Signature**:
  ```python
  def prompt_text(self, prompt_msg: str, default: Optional[str] = None) -> str
  ```
* **Inputs**:
  - `prompt_msg` (`str`): Input question label.
  - `default` (`Optional[str]`): Optional fallback string.
* **Outputs**: `str` (User typed text or default string).
* **Description**: Prompts user for raw text string input.

#### `prompt_confirm`
* **Full Signature**:
  ```python
  def prompt_confirm(self, prompt_msg: str, default: bool = True) -> bool
  ```
* **Inputs**:
  - `prompt_msg` (`str`): Confirmation question string.
  - `default` (`bool`): Default choice if user presses Enter (`True` for Yes, `False` for No).
* **Outputs**: `bool` (`True` if confirmed, `False` otherwise).
* **Description**: Prompts user for a binary yes/no confirmation.

#### `display_summary`
* **Full Signature**:
  ```python
  def display_summary(self, title: str, items: Dict[str, Any]) -> None
  ```
* **Inputs**:
  - `title` (`str`): Section title header.
  - `items` (`Dict[str, Any]`): Key-value pairs to display in summary box.
* **Outputs**: `None`
* **Description**: Renders a formatted summary table box in the terminal console.

---

### 🪵 Service 2: Professional Terminal Logger Service
* **File Path**: `src/services/logger_service.py`
* **Class**: `LoggerService` (Factory helper: `get_logger(name)`)
* **Description**: Provides Rich console logging, timestamped log formats, step banners, prompt inspector tables, file log handlers, and execution dashboards.

#### `get_logger` & `configure_qa_logger`
* **Full Signatures**:
  ```python
  def get_logger(name: str = "QAAgent", log_file: Optional[Union[str, Path]] = None) -> LoggerService
  def configure_qa_logger(temp_dir: Union[str, Path]) -> Path
  ```
* **Inputs**:
  - `name` (`str`): Module tag name for the logger (e.g. `"Main"`, `"IngestTargetNode"`).
  - `temp_dir` (`Union[str, Path]`): Workspace directory to attach `.temp/[run_id]/logs/qa_agent.log`.
* **Outputs**:
  - `get_logger`: `LoggerService` instance.
  - `configure_qa_logger`: `Path` to configured log file.
* **Description**: Obtains named logger instances and configures per-run file log handlers.

#### `info`, `success`, `warning`, `error`, `debug`
* **Full Signatures**:
  ```python
  def info(self, msg: str, *args, **kwargs) -> None
  def success(self, msg: str, *args, **kwargs) -> None
  def warning(self, msg: str, *args, **kwargs) -> None
  def error(self, msg: str, *args, **kwargs) -> None
  def debug(self, msg: str, *args, **kwargs) -> None
  ```
* **Inputs**: Log message string and positional/keyword formatting arguments.
* **Outputs**: `None`
* **Description**: Writes colored log lines with timestamp tags `[INFO]`, `[SUCCESS]`, `[WARN]`, `[ERROR]`, `[DEBUG]` to console and active log files.

#### `step`
* **Full Signature**:
  ```python
  def step(self, step_num: Any, title: str) -> None
  ```
* **Inputs**: Step identifier number/string, step title string.
* **Outputs**: `None`
* **Description**: Prints a centered step banner panel in the terminal console.

#### `table_summary` & `token_dashboard`
* **Full Signatures**:
  ```python
  def table_summary(self, title: str, items: Dict[str, Any], ...) -> None
  ```
* **Inputs**: Dashboard title, key-value dictionary or node-token consumption dict.
* **Outputs**: `None`
* **Description**: Prints Rich structured tables for key-value state parameters or LLM token usage.

---

### 💾 Service 3: Checkpoint & Recovery Service
* **File Path**: `src/services/checkpoint_service.py`
* **Description**: Handles state persistence, crash recovery, and `--resume` state serialization via `.temp/{run_id}/state.json`.

#### `get_checkpoint_path`
* **Full Signature**:
  ```python
  def get_checkpoint_path(workspace_dir: Union[str, Path]) -> Path
  ```
* **Inputs**: `workspace_dir` (`Union[str, Path]`): Active run workspace path.
* **Outputs**: `Path` (Path to `.temp/{run_id}/state.json`).
* **Description**: Resolves state checkpoint file location.

#### `save_checkpoint`
* **Full Signature**:
  ```python
  def save_checkpoint(workspace_dir: Union[str, Path], state: Dict[str, Any]) -> Path
  ```
* **Inputs**:
  - `workspace_dir` (`Union[str, Path]`): Active run workspace path.
  - `state` (`Dict[str, Any]`): Active `QAState` dictionary.
* **Outputs**: `Path` (Saved checkpoint file path).
* **Description**: Serializes current `QAState` snapshot to `state.json` safely.

#### `load_checkpoint`
* **Full Signature**:
  ```python
  def load_checkpoint(workspace_dir: Union[str, Path]) -> Optional[Dict[str, Any]]
  ```
* **Inputs**: `workspace_dir` (`Union[str, Path]`): Workspace directory path.
* **Outputs**: `Optional[Dict[str, Any]]` (Loaded state dict or `None` if missing).
* **Description**: Reads and deserializes `state.json` checkpoint for workflow resumption.

#### `has_checkpoint` & `clear_checkpoint`
* **Full Signatures**:
  ```python
  def has_checkpoint(workspace_dir: Union[str, Path]) -> bool
  def clear_checkpoint(workspace_dir: Union[str, Path]) -> None
  ```
* **Inputs**: `workspace_dir` (`Union[str, Path]`): Workspace directory path.
* **Outputs**: `bool` for `has_checkpoint`, `None` for `clear_checkpoint`.
* **Description**: Checks existence of or deletes `state.json` file.

---

### 🔍 Service 4: AST Analysis & File Classification Service
* **File Path**: `src/services/ast_service.py`
* **Class**: `ASTService` (Singleton: `ast_service`)
* **Description**: Evaluates workspace files against Node 3 `logic_signatures` & `language_rules` to classify them as `TESTABLE` vs `NON-TESTABLE`.

#### `classify_file`
* **Full Signature**:
  ```python
  def classify_file(
      self,
      file_path: Path,
      workspace_dir: Path,
      logic_signatures: Dict[str, Any],
      language_rules: Dict[str, Any]
  ) -> Tuple[bool, Dict[str, Any]]
  ```
* **Inputs**:
  - `file_path` (`Path`): Path to target source file to audit.
  - `workspace_dir` (`Path`): Path to project root directory.
  - `logic_signatures` (`Dict[str, Any]`): Control flow keywords, handler patterns, and negative signature arrays.
  - `language_rules` (`Dict[str, Any]`): Extension filters and non-testable filenames.
* **Outputs**: `Tuple[bool, Dict[str, Any]]`
  - `is_testable` (`bool`): `True` if file requires unit test generation, `False` if skipped.
  - `audit_info` (`Dict[str, Any]`): Detailed audit record dict.
    - If `False`: `{"source_file": str, "reason": str, "skipped_by": str, "matched_signature_key": Optional[str]}`.
    - If `True`: `{"source_file": str, "status": "TESTABLE"}`.
* **Description**: Checks extensions, non-testable filenames, empty 0-byte content, unreadable binary files, and negative AST code signatures (e.g. `settings =`, `__all__ =`).

---

### 🐳 Service 5: Sandbox Container Service
* **File Path**: `src/services/sandbox_service.py`
* **Class**: `SandboxService` (Singleton: `sandbox_service`)
* **Description**: Controls Docker SDK container creation, image layer caching, workspace volume mounting, and 30s timeout test execution.

#### `build_or_get_image`
* **Full Signature**:
  ```python
  def build_or_get_image(
      self,
      workspace_dir: Path,
      image_name: str,
      dockerfile_content: Optional[str] = None
  ) -> str
  ```
* **Inputs**:
  - `workspace_dir` (`Path`): Path to project root workspace.
  - `image_name` (`str`): Image tag (e.g. `qa-agent-express:sha256_hash`).
  - `dockerfile_content` (`Optional[str]`): Generated Dockerfile content string.
* **Outputs**: `str` (Docker image tag string).
* **Description**: Checks local Docker image cache. On cache miss, writes `Dockerfile.qa` and builds image layer.

#### `start_sandbox_container`
* **Full Signature**:
  ```python
  def start_sandbox_container(
      self,
      image_name: str,
      container_name: str,
      workspace_dir: Path
  ) -> str
  ```
* **Inputs**:
  - `image_name` (`str`): Docker image tag name.
  - `container_name` (`str`): Container instance name.
  - `workspace_dir` (`Path`): Project root directory to mount into `/app`.
* **Outputs**: `str` (Active Docker Container ID string).
* **Description**: Starts background container (`tail -f /dev/null`) with read-write volume mount `/app`.

#### `execute_test_command`
* **Full Signature**:
  ```python
  def execute_test_command(
      self,
      container_id_or_name: str,
      test_command: str,
      timeout_sec: int = 30
  ) -> Dict[str, Any]
  ```
* **Inputs**:
  - `container_id_or_name` (`str`): Container ID or name string.
  - `test_command` (`str`): Command to execute (e.g. `pytest tests/test_api.py`).
  - `timeout_sec` (`int`): Maximum execution timeout in seconds (default 30s).
* **Outputs**: `Dict[str, Any]` containing `{"exit_code": int, "raw_logs": str, "execution_time_ms": int, "timed_out": bool}`.
* **Description**: Runs command inside container using `exec_run`, measuring runtime and enforcing timeout guardrails.

#### `stop_and_remove_container`
* **Full Signature**:
  ```python
  def stop_and_remove_container(self, container_id_or_name: str) -> None
  ```
* **Inputs**: `container_id_or_name` (`str`): Target container ID/name string.
* **Outputs**: `None`
* **Description**: Stops and removes active container instance while preserving image layer cache.

---

## 3. LLM Provider Interfaces (`src/llm_provider/`)

### Factory (`src/llm_provider/factory.py`)
* **`LLMProviderFactory.create_provider(provider_type: Optional[str] = None) -> BaseLLMProvider`**
  * *Inputs:* Optional provider string (`"docker"`, `"gemini"`, `"openai"`). Reads `.env` `LLM_PROVIDER` if omitted.
  * *Outputs:* Instantiated concrete `BaseLLMProvider` instance.

### Abstract Base Provider (`src/llm_provider/providers/base_provider.py`)
* **`generate(prompt: str, system_prompt: Optional[str] = None) -> str`**
  * *Inputs:* Prompt text string, optional system prompt string.
  * *Outputs:* Clean LLM response text string.
* **`generate_structured(prompt: str, schema: Type[BaseModel]) -> BaseModel`**
  * *Inputs:* Prompt text string, target Pydantic `BaseModel` schema class.
  * *Outputs:* Parsed Pydantic model object.

---

## 4. LangGraph Workflow Schemas (`src/workflow/state.py`)

* **`NonTestableFile` (TypedDict)**: `{"source_file": str, "reason": str, "skipped_by": str, "matched_signature_key": Optional[str]}`
* **`TestResultFile` (TypedDict)**: `{"source_file": str, "test_file": str, "status": str, "failure_category": Optional[str], "retries_used": int, "execution_time_ms": int}`
* **`QAState` (TypedDict)**: Formal 24-field state dictionary tracking ingestion inputs, ecosystem profiler results, queues, container IDs, and token budget caps.

---

## 5. Node Creation & Graph Registration Protocol

Whenever a new LangGraph Node is added to the system, you **MUST** follow this strict 5-step registration protocol:

1. **Step 1: Create Node File (`src/workflow/nodes/<node_name>.py`)**:
   - Write the node function accepting `state: QAState` and returning `Dict[str, Any]` state updates.
   - Use `logger = get_logger("<NodeName>")` for node log output.

2. **Step 2: Export Node (`src/workflow/nodes/__init__.py`)**:
   - Import the new node function in `src/workflow/nodes/__init__.py` and add its name to `__all__`.

3. **Step 3: Register in StateGraph (`src/workflow/graph.py`)**:
   - Import the node function in `src/workflow/graph.py`.
   - Register the node in `build_graph()`:
     ```python
     builder.add_node("node_name", node_fn)
     ```

4. **Step 4: Connect Graph Edges (`src/workflow/graph.py`)**:
   - Wire the control flow transition edge using standard edges:
     ```python
     builder.add_edge("previous_node", "node_name")
     builder.add_edge("node_name", "next_node")
     ```
   - Or add conditional routing logic if the node splits control flow:
     ```python
     builder.add_conditional_edges("node_name", routing_function, {"path_a": "node_a", "path_b": "node_b"})
     ```

5. **Step 5: Update State Schema (`src/workflow/state.py`)**:
   - If the new node introduces or mutates new keys in the state payload, add the corresponding typed fields to `QAState` in `src/workflow/state.py`.

---

## 6. Token Tracking & Accounting Standard

1. **Global Token Running Total (`total_tokens_used: int`)**:
   - Stores the cumulative total tokens consumed across all LLM calls during the run.

2. **Per-Node Token Ledger (`node_tokens: Dict[str, int]`)**:
   - Maps each node identifier to its cumulative token consumption (e.g. `{"detect_ecosystem_node": 75, "generate_test_node": 1420}`).

3. **Per-File Token Ledger (`TestResultFile["tokens_used"]: int`)**:
   - Records the exact tokens spent generating and self-healing test cases for a specific source file.

