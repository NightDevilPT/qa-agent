# AI Developer Rulebook: QA Agent

> **Mission**
> The QA Agent is a state-driven, autonomous testing pipeline for JavaScript and TypeScript. It uses **LangGraph** for orchestration, a **persistent Docker sandbox** (`utils/sandbox.py`) for execution, and **LangChain** for LLM calls. Follow this document and [README.md](../README.md). Track build progress in [nodes-and-tools.md](./nodes-and-tools.md).

---

## 1. Project structure and file placement

Every feature belongs in **one** folder. Do not mix responsibilities.

| Component | Folder | Rules |
|-----------|--------|--------|
| **CLI entry** | `src/main.py` | Collect user input (path, language, work type), build initial `QAState`, call `compile_graph().invoke()`. Show summary UI. **No** test loops, LLM calls, or Docker logic here. |
| **Graph nodes** | `src/workflow/nodes/` | One file per node. Signature: `def node_name(state: QAState) -> dict`. Return **only** keys to update. |
| **State and graph** | `src/workflow/` | `state.py` = types. `graph.py` = `StateGraph` wiring and conditional edges. |
| **Utilities** | `src/utils/` | Stateless helpers shared by nodes and CLI. **Never** `import workflow` from `utils`. |
| **Middleware** | `src/middleware/` | LangChain **decorator** hooks only (`@before_model`, `@after_model`, etc.). |
| **Constants** | `src/constants/` | Configuration data only — no business logic, no I/O. |
| **Language configs** | `src/constants/languages/` | Per-language Docker/Jest/exclude settings (`javascript.py`, `typescript.py`, `config.py`). |

### `src/constants/` layout

| Path | Purpose |
|------|---------|
| `constants/languages/javascript.py` | `JAVASCRIPT_CONFIG` dict |
| `constants/languages/typescript.py` | `TYPESCRIPT_CONFIG` dict |
| `constants/languages/config.py` | Registry: `get_language_config()`, `normalize_project_language()`, `get_extensions_for_language()`, `get_all_exclude_patterns()` |
| `constants/languages/__init__.py` | Public exports via `__all__` |
| `constants/<topic>.py` *(future)* | Non-language constants (e.g. default retries, app name) — **add new files here**, not in `utils` |

**Language-specific values** (image, `install_cmd`, `test_cmd`, `exclude_patterns`, `config_files`, workspace layout) **must** live in `javascript.py` / `typescript.py`, not hardcoded in nodes or sandbox.

---

## 2. Logging and terminal output (mandatory)

### Use `utils/logger.py` — never bare `print()`

| Location | What to use |
|----------|-------------|
| **Nodes**, **utils**, orchestration code | `from utils.logger import get_logger` → `log.info()`, `log.start()`, `log.end()`, `log.warn()`, `log.error()`, `log.section()` |
| **CLI** (`main.py`) | `get_logger("main")` for workflow logs; `from utils.logger import console` for Rich `Panel`, `Table`, `Prompt` |
| **Do not** | `print()`, a second `Console()`, or ad-hoc `logging.basicConfig()` in feature code |

**Node pattern:**

```python
from utils.logger import get_logger

log = get_logger("extract_files")

def extract_files(state: QAState) -> dict:
    log.start("Node entered")
    log.info("Scan target path=%s", state["target_path"])
    # ...
    log.end("status=OK discovered_files=%d", count)
    return {"discovered_files": files}
```

**CLI pattern:**

```python
from utils.logger import console, get_logger

log = get_logger("main")
console.print(Panel.fit("QA Agent"))  # UI only
log.start("Orchestrator started")
```

### Human input (menus, approve/reject)

| Use case | Module |
|----------|--------|
| Simple path / language prompts in CLI | `main.py` with `Prompt.ask(..., console=console)` and shared `console` from `utils.logger` |
| Multi-option decisions inside workflow | `from utils.hitl import ask_human` — **not** `input()` in nodes |

Nodes must **not** call `input()` or Typer directly. Prefer collecting choices in `main.py` and passing them via `QAState` (e.g. `project_language`, `input_type`).

---

## 3. Utilities — which file to use

Create **new** shared behavior in `src/utils/` (one concern per file). Export public API in `utils/__init__.py` → `__all__`.

| Need | File | Use |
|------|------|-----|
| Terminal workflow logs + shared Rich console | `utils/logger.py` | `get_logger()`, `console` |
| LLM client (Docker / Gemini) | `utils/llm.py` | `get_llm()` only — never instantiate `ChatOpenAI` in nodes |
| Docker sandbox / Jest execution | `utils/sandbox.py` | `Sandbox`, `create_sandbox()` — **all** container and test runs |
| Human approval / choice menus | `utils/hitl.py` | `ask_human()` |
| Prompt text for LLM nodes *(planned)* | `utils/prompts.py` | `build_plan_prompt`, `build_generate_prompt`, `build_fix_prompt` |
| Path validation / repo clone *(planned)* | `utils/paths.py`, `utils/repo.py` | Path helpers only |
| Cross-run file ledger *(planned)* | `utils/ledger.py` | `.qa-agent/ledger.json` read/write |

**Do not** put Docker logic in nodes except calling `sandbox` methods. **Do not** put language Docker images or Jest config strings in `utils`.

---

## 4. Middleware (LangChain only)

All middleware lives in `src/middleware/`. Use **native LangChain decorator hooks**, not custom wrapper classes.

| Rule | Detail |
|------|--------|
| **Hooks** | `@before_agent`, `@after_agent`, `@before_model`, `@after_model`, `@wrap_model_call`, `@wrap_tool_call` |
| **Factory** | Export e.g. `create_logger_middleware()` from `middleware/logger.py` |
| **SRP** | One file per concern (`logger.py`, future `rate_limit.py`) |
| **Exports** | Register in `middleware/__init__.py` → `__all__` |
| **Attachment** | Wire middleware when building LLM/agent in nodes — **not** in `main.py` business flow |

Reference implementation: `src/middleware/logger.py`.

Middleware is for **LLM/agent observability**. Workflow step logs use **`utils/logger.py`**, not middleware.

---

## 5. Docker sandbox rules

Security: **never** execute LLM-generated code on the host. Always use `utils/sandbox.py`.

| Rule | Requirement |
|------|-------------|
| **Persistent container** | `init_docker` node: create **one** container per run, run `npm install` **once**, keep alive |
| **Append, don't recreate** | New tests/sources are written to the **mounted workspace**; reuse the same container for every file in the todo loop |
| **No per-file containers** | Do not call `containers.run()` for each test file after init (refactor legacy `execute_tests` toward `exec` on the live container) |
| **Isolation** | `mem_limit` (e.g. `1g`), command `timeout` (e.g. `120s`), `network_mode` only when install needs it |
| **Teardown** | `teardown` node or `main.py` `finally`: `container.remove(force=True)` even on failure |
| **Config source** | Image, install/test commands, workspace layout from `get_language_config(state["project_language"])` |

Nodes: `init_docker`, `run_test`, `teardown` call sandbox APIs only.

---

## 6. LangGraph and state

Driven by `src/workflow/state.py` and `src/workflow/graph.py`.

1. **Partial updates:** Nodes return only changed `QAState` keys; LangGraph merges them.
2. **CLI input → state:** `main.py` sets `target_path`, `input_type`, `project_language`, `max_retries` before `invoke()`.
3. **Ledger:** `todo_list` = queue; `file_statuses` = completed work per path.
4. **Planning:** `plan_strategy` uses `with_structured_output(PlanStrategyOutput)` — no regex on raw LLM text.
5. **Per-file language:** `project_language` is set at CLI; `current_language` may mirror it or come from `detect_language()` for a single file.

### Initial state from CLI (example)

```python
graph.invoke({
    "target_path": str(resolved_path),
    "input_type": "file",  # or "folder" | "repo"
    "project_language": "javascript",  # or "typescript"
    "max_retries": 3,
})
```

---

## 7. LLM rules

1. **Entry point:** `from utils.llm import get_llm` — supports Docker (Qwen) and Gemini via env.
2. **Planning:** `get_llm().with_structured_output(PlanStrategyOutput)`.
3. **Generation / fix:** `get_llm().invoke(prompt)`; prompts built in `utils/prompts.py` when added.
4. **Self-heal prompt must include:** original source, failing test code, trimmed sandbox `stderr`/`stdout`.
5. **Token discipline:** Do not pass full `QAState` to the LLM; only fields needed for that node.

---

## 8. Language and extraction rules

1. User selects **javascript** or **typescript** in `main.py` → `project_language` in state.
2. `extract_files` scans extensions from `get_extensions_for_language(project_language)` only.
3. Excludes use `get_all_exclude_patterns()` from language configs plus project `.gitignore`.
4. Adding a language: new `constants/languages/<lang>.py` + register in `LANGUAGE_CONFIG` — **do not** change graph structure for JS/TS-only differences.

---

## 9. SOLID (non-negotiable)

| Principle | Rule |
|-----------|------|
| **SRP** | One node = one step. Do not combine generate + run in one function. |
| **OCP** | New language = new config file under `constants/languages/`. |
| **Dependency inversion** | Nodes use `get_language_config()`, `get_llm()`, `create_sandbox()` — no `if language == "javascript"` blocks in nodes. |

---

## 10. Imports and `__init__.py`

1. **Absolute imports from `src` root** (run with `PYTHONPATH=src` or project script):

   - Wrong: `from src.utils.llm import get_llm`
   - Correct: `from utils.llm import get_llm`

2. **`__all__`:** Every new public symbol in `utils`, `middleware`, `workflow`, `workflow/nodes`, `constants/languages` must be listed in that package's `__init__.py`.

3. **Dependencies:** Do not add packages unless requested. Stack: `langgraph`, `langchain`, `docker`, `rich`, `pydantic`, `pathspec`, etc. (see `pyproject.toml`).

---

## 11. Quick reference — do / don't

| Do | Don't |
|----|--------|
| `log = get_logger("node_name")` in nodes | `print()` in nodes or utils |
| `create_sandbox()` for Docker | `docker.from_env()` inside nodes |
| `get_llm()` for models | Direct OpenAI/Gemini clients in nodes |
| `ask_human()` for multi-choice HITL | `input()` in nodes |
| `get_language_config(project_language)` | Hardcoded `node:20-alpine` in nodes |
| `exclude_patterns` in `javascript.py` / `typescript.py` | Hardcoded ignore lists in `extract_files` |
| `@before_model` middleware for LLM traces | Custom middleware classes |
| `constants/` for config dicts | Config blobs inside `utils` |
| Return `{key: value}` from nodes | Return full `state` object |

---

## 12. Related docs

| Document | Content |
|----------|---------|
| [README.md](../README.md) | Architecture, persistent sandbox, Mermaid flow |
| [nodes-and-tools.md](./nodes-and-tools.md) | Checklist, build levels, node status |

---

*Align all new code with this rulebook. When in doubt, match existing files: `main.py`, `utils/logger.py`, `workflow/nodes/extract_files.py`, `constants/languages/`, `middleware/logger.py`.*
