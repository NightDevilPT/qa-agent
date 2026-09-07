# Autonomous QA Agent - Codebase Structure & Installed Dependencies Guide

This document details the complete modular directory layout incorporating `main.py` interactive entrypoint using `uv`, the `src/llm_provider/` factory pattern, and `src/services/` architecture.

---

## 1. Project Directory Layout

```
qa-agents/
├── main.py                           # Root Entrypoint & Interactive CLI Trigger (uv run main.py)
├── .env                              # Active Environment Configuration (LLM_PROVIDER, API Keys)
├── .env.example                      # Environment Configuration Template
├── pyproject.toml                    # UV Project Configuration & Dependencies
├── README.md                         # Project Overview & Usage Guide
│
├── docs/                             # Complete Specification Suite
│   ├── QA_AGENT_FLOW.md              # High-Level Architecture & Execution Flow
│   ├── LANGGRAPH_NODES_SPEC.md       # LangGraph 13-Node Technical Specification
│   ├── PROJECT_STRUCTURE.md          # Codebase Layout & Dependencies Reference
│   └── RULES.md                      # System Architecture Rulebook & Abstract Service Interfaces
│
└── src/                              # Main Application Source Code
    ├── __init__.py
    ├── config.py                     # Config & Env Settings (Pydantic Settings)
    │
    ├── llm_provider/                 # Pluggable LLM Provider Factory System
    │   ├── __init__.py
    │   ├── factory.py                # LLMProviderFactory (Loads provider from .env)
    │   └── providers/                # Concrete Provider Implementations
    │       ├── __init__.py
    │       ├── base_provider.py      # Abstract BaseLLMProvider Class
    │       ├── docker_provider.py    # Local Docker Model Provider ('docker')
    │       ├── gemini_provider.py    # Google Gemini Provider ('gemini')
    │       └── openai_provider.py    # OpenAI Model Provider ('openai')
    │
    ├── services/                     # Core Business Services & Engine Components
    │   ├── __init__.py
    │   ├── terminal_service.py       # Interactive Terminal UI, Menus, Prompts & Dialogs
    │   ├── logger_service.py         # Rich Logging, Formatting & Progress Bar Services
    │   ├── checkpoint_service.py     # Local state.json Checkpoint & Snapshot Manager
    │   ├── ast_service.py            # Node 4 File Classification Service (logic_signatures & language_rules)
    │   └── sandbox_service.py        # Docker SDK Container & Sandbox Lifecycle Manager
    │
    └── workflow/                     # LangGraph State Machine Architecture
        ├── __init__.py
        ├── state.py                  # TypedDict QAState Schema Definition
        ├── graph.py                  # StateGraph Construction & Router Rules
        └── nodes/                    # 13 LangGraph Node Implementations
            ├── __init__.py
            ├── ingest_target.py          # Node 1: Interactive Target Ingestion
            ├── clone_workspace.py         # Node 2: Workspace Cloning
            ├── detect_ecosystem.py        # Node 3: Ecosystem Profiling & Manifest Cache
            ├── classify_files.py          # Node 4: Transitive Hash & AST Clustering
            ├── topological_sort.py        # Node 5: Parallel Level Grouping
            ├── setup_docker.py            # Node 6: LLM Dockerfile & Sandbox Setup
            ├── select_next_file.py        # Node 7: Batch Queue Selector
            ├── check_existing_test.py     # Node 8: Existing Test JIT Inspector & Router
            ├── generate_test.py           # Node 9: LLM Test Generator & Fan-Out
            ├── execute_docker_test.py     # Node 10: Docker Exec with 30s Timeout
            ├── self_heal_test.py          # Node 11: Tooling vs Bug Self-Healer
            ├── generate_report.py         # Node 12: Summary Report & Token Cap
            └── teardown_sandbox.py        # Node 13: Container Teardown
```

---

## 2. Pluggable LLM Provider System (`src/llm_provider/`)

The active LLM provider is **read strictly from `LLM_PROVIDER` in `.env`** (`LLM_PROVIDER=docker`, `LLM_PROVIDER=gemini`, or `LLM_PROVIDER=openai`).

```python
from src.llm_provider.factory import LLMProviderFactory

# Automatically loads active provider configured in .env (LLM_PROVIDER=docker|gemini|openai)
llm = LLMProviderFactory.create_provider()
```

| Provider Key | Class File                     | Configured in `.env`                                |
| :----------- | :----------------------------- | :-------------------------------------------------- |
| `"docker"`   | `providers/docker_provider.py` | `LLM_PROVIDER=docker` (Local Docker model endpoint) |
| `"gemini"`   | `providers/gemini_provider.py` | `LLM_PROVIDER=gemini` (Google Gemini Cloud API)     |
| `"openai"`   | `providers/openai_provider.py` | `LLM_PROVIDER=openai` (OpenAI Cloud API)            |

---

## 3. Interactive Execution Flow (`uv run main.py`)

We manage Python virtual environments and dependencies exclusively using **`uv`**.

Running `uv run main.py` triggers Node 1 (`ingest_target_node`), presenting an interactive menu powered by `terminal_service`:

```bash
# 1. Launch the Autonomous QA Agent (Provider read from .env)
uv run main.py

# 2. Non-interactive CI mode (Optional)
uv run main.py --target=./my-express-api --skip-existing=always
```

### Interactive Menu Sequence on `uv run main.py`:

```
============================================================
  AUTONOMOUS QA AGENT SYSTEM
  LangGraph Automated Test Generation & Sandbox Execution
============================================================

? Select Target Input Mode:
  [1] Single File (Generate test for 1 file)
  [2] Folder Path (Generate tests for full folder/project) (default)
  [3] Git Repository URL (Clone public repo and generate tests)

Select option [1-3] (default 2): 2

? Enter target folder path: ./my-express-api
  Target resolved: c:\Users\Pawan\Desktop\my-express-api
  Saved into QAState: input_mode='FOLDER', target_path='./my-express-api'
```

---

## 4. Service Component Responsibilities (`src/services/`)

| Service Component        | File / Path                          | Responsibility & Role                                                                                                                                        |
| :----------------------- | :----------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Root Entrypoint**      | `main.py`                            | Executed via `uv run main.py`. Triggers Node 1 interactive prompt menu and executes LangGraph state graph.                                                   |
| **Terminal UI Service**  | `src/services/terminal_service.py`   | Handles ANSI color rendering, interactive input mode selection menus, path validation, confirmation dialogs, and styled summary boxes.                       |
| **Logger Service**       | `src/services/logger_service.py`     | Manages Rich console logging, spinner animations during LLM execution, and formatted error logs.                                                             |
| **Checkpoint Service**   | `src/services/checkpoint_service.py` | Reads and writes snapshot checkpoints to `.temp/{name}-{uuid}/state.json` for crash recovery and instant `--resume`.                                         |
| **AST Analysis Service** | `src/services/ast_service.py`        | Single-purpose service for Node 4 file classification (matching `logic_signatures` & `language_rules` from `QAState`).                                       |
| **Sandbox Service**      | `src/services/sandbox_service.py`    | Controls Docker SDK container lifecycle (`qa-agent-{foldername}`), single-instance LLM Dockerfile generation, layer caching, and 30s `docker exec` timeouts. |

---

## 5. Installed Dependencies & Technical Purpose

Below is the complete breakdown of the lean, 15-package dependency list in `pyproject.toml`:

| Package Name                 | Installed Version | Technical Purpose in QA Agent Architecture                                                                                                                     |
| :--------------------------- | :---------------- | :------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`langgraph`**              | `>=1.2.1`         | **State Orchestration Engine:** Drives the 13-node state graph, manages conditional routing, checkpoint persistence, and `Send()` API parallel worker fan-out. |
| **`langchain`**              | `>=1.3.1`         | **LLM Framework Core:** Provides standard abstractions for chains, prompts, and model interactions.                                                            |
| **`langchain-core`**         | `>=1.4.0`         | Base interfaces for messages, runnables, and output parsers.                                                                                                   |
| **`langchain-openai`**       | `>=1.2.2`         | Provider integration for OpenAI GPT-4o / GPT-4o-mini models.                                                                                                   |
| **`langchain-google-genai`** | `>=4.2.4`         | Provider integration for Google Gemini Flash / Pro models.                                                                                                     |
| **`docker`**                 | `>=7.1.0`         | **Docker SDK for Python:** Programmatically manages containers, image builds, layer caching, and isolated `docker exec` test execution without using host OS.  |
| **`tree-sitter`**            | `>=0.25.2`        | **Universal AST Engine:** Language-agnostic Concrete Syntax Tree parser used for function body pruning, AST shape hashing, and structural clustering.          |
| **`typer`**                  | `>=0.25.1`        | **CLI Application Framework:** Drives CLI commands (`uv run main.py`), options (`--skip-existing=ask`), and flags.                                             |
| **`rich`**                   | `>=15.0.0`        | **Terminal UI:** Beautiful progress bars, status tables, colored logs, and interactive CLI prompts `[y/N]`.                                                    |
| **`pydantic`**               | `>=2.13.4`        | Data validation and type enforcement for state update payloads and LLM JSON outputs.                                                                           |
| **`pydantic-settings`**      | `>=2.14.1`        | Loads and validates `.env` environment variables (`OPENAI_API_KEY`, `MAX_TOKEN_BUDGET`).                                                                       |
| **`gitpython`**              | `>=3.1.50`        | Git repository management for cloning target public Git repositories into `.temp/workspace/`.                                                                  |
| **`pathspec`**               | `>=1.1.1`         | Match files against `.gitignore` patterns to skip non-code files locally.                                                                                      |
| **`httpx`**                  | `>=0.28.1`        | Async HTTP client for external API requests and model endpoint communication.                                                                                  |
| **`python-dotenv`**          | `>=1.2.2`         | Explicit `.env` environment variable loading.                                                                                                                  |
