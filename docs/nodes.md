# Complete Nodes List — What We Need to Build

---

## Total: 9 Action Nodes + 3 Conditional Routers = 12 Components

---

## Action Nodes (9)

### Node 1: `extract_files`
| | |
|---|---|
| **File** | `src/workflow/nodes/extract_files.py` |
| **Phase** | 1 — Ingestion |
| **Uses LLM?** | No |
| **Signature** | `def extract_files(state: QAState) -> dict` |

**Purpose:** Takes CLI input (file/folder/repo), creates `.temp/qa-agent-{uuid}` workspace, copies/clones project into it, scans for testable files.

**Reads from state:**
- `target_path` — path or repo URL
- `input_type` — `"file"` | `"folder"` | `"repo"`
- `project_language` — `"javascript"` | `"typescript"`

**Returns to state:**
- `workspace_path` — absolute path to `.temp/qa-agent-{uuid}/workspace`
- `discovered_files` — list of relative file paths found

**Logic:**
- Generate workspace at `.temp/qa-agent-{random_id}/workspace`
- If `repo` → `git clone` into workspace
- If `folder` → copy entire folder into workspace
- If `file` → create `src/` in workspace, copy file there
- Walk workspace, find files matching language extensions
- Apply exclude patterns from language config + `.gitignore`
- Filter out existing test files

**Next:** → `analyze_test_lib`

---

### Node 2: `analyze_test_lib`
| | |
|---|---|
| **File** | `src/workflow/nodes/analyze_test_lib.py` |
| **Phase** | 2 — Analysis |
| **Uses LLM?** | No |
| **Signature** | `def analyze_test_lib(state: QAState) -> dict` |

**Purpose:** Reads actual project files to detect test framework, module system, dependencies, TypeScript usage, import patterns. Generates complete `test_lib_config` for downstream nodes.

**Reads from state:**
- `workspace_path`
- `discovered_files`
- `project_language`

**Returns to state:**
- `project_analysis` — single object containing ALL analysis results:
  - `test_lib` — `"jest"` | `"vitest"` | `"mocha"` | `"jasmine"` | `"none"`
  - `test_lib_config` — install packages, config files, test command, framework hints
  - `module_system` — `"esm"` | `"commonjs"` | `"mixed"`
  - `uses_typescript` — boolean
  - `has_package_json` — boolean
  - `project_dependencies` — all deps from package.json
  - `external_dependencies` — external packages found in imports
  - `per_file_imports` — map of file → list of imports
  - `path_aliases` — from tsconfig
  - `existing_test_config` — found test config content
  - `existing_test_files` — already present test files
  - `entry_points` — main files
  - `is_monorepo` — boolean
  - `language_config` — full language config reference

**Logic:**
- Read `package.json` → detect test framework from deps
- If no framework found → use `default_test_lib` from language config
- Look up framework in `available_test_libs` → get full config
- Read `tsconfig.json` → extract compiler options, path aliases
- Scan every discovered file → detect import/require patterns
- Build `per_file_imports` map
- Collect external dependency names
- Check for existing test files and configs
- Generate complete `test_lib_config` with install packages, commands, hints

**Next:** → `plan_strategy`

---

### Node 3: `plan_strategy`
| | |
|---|---|
| **File** | `src/workflow/nodes/plan_strategy.py` |
| **Phase** | 3 — Planning |
| **Uses LLM?** | Yes — with structured output (`PlanStrategyOutput`) |
| **Signature** | `def plan_strategy(state: QAState) -> dict` |

**Purpose:** Uses LLM to decide which files are testable, builds dependency graph, creates prioritized todo list.

**Reads from state:**
- `discovered_files`
- `project_analysis` — specifically: `per_file_imports`, `external_dependencies`, `existing_test_files`, `module_system`, `uses_typescript`

**Returns to state:**
- `todo_list` — priority-ordered list of files to test
- `dependency_graph` — map of file → its dependencies
- `skipped_files` — files skipped with reason
- `file_statuses` — initialized ledger for all files

**Logic:**
- Build prompt with discovered files + import information
- LLM classifies each file: TEST or SKIP (with reason)
- For testable files: determines dependencies from `per_file_imports`
- Sorts by dependency depth (no-deps first)
- Returns structured output via `with_structured_output(PlanStrategyOutput)`

**Next:** → `after_plan` (router R1)

---

### Node 4: `init_docker`
| | |
|---|---|
| **File** | `src/workflow/nodes/init_docker.py` |
| **Phase** | 4 — Environment Setup |
| **Uses LLM?** | No |
| **Signature** | `def init_docker(state: QAState) -> dict` |

**Purpose:** Creates persistent Docker container, mounts workspace, installs all dependencies once.

**Reads from state:**
- `workspace_path`
- `project_analysis` — specifically: `test_lib_config`, `has_package_json`, `uses_typescript`, `module_system`, `language_config`

**Returns to state:**
- `container_id` — Docker container ID
- `sandbox_ready` — `True`

**Logic:**
- Get Docker image from `language_config`
- Create container with `tail -f /dev/null` (persistent)
- Mount workspace at `/workspace`
- If project has `package.json` → run `npm install` (installs existing deps + test lib if missing)
- If no `package.json` → generate one with `test_lib_config.install_packages`, then `npm install`
- Generate framework config files (`jest.config.js`, `tsconfig.json`, etc.) from `test_lib_config.config_files`
- Container stays running for entire workflow

**Next:** → `select_next_file`

---

### Node 5: `select_next_file`
| | |
|---|---|
| **File** | `src/workflow/nodes/select_next_file.py` |
| **Phase** | 5 — Worker Loop |
| **Uses LLM?** | No |
| **Signature** | `def select_next_file(state: QAState) -> dict` |

**Purpose:** Pops next PENDING file from todo list, sets as current work item.

**Reads from state:**
- `todo_list`
- `file_statuses`

**Returns to state:**
- `current_file` — next file path or `None`
- `retry_count` — reset to `0`
- Updated `file_statuses` — marks file as `IN_PROGRESS`

**Logic:**
- Find first item in `todo_list` with status `PENDING`
- If found → set `current_file`, mark `IN_PROGRESS`, reset `retry_count`
- If not found → set `current_file = None`

**Next:** → `after_select_next` (router R2)

---

### Node 6: `generate_test`
| | |
|---|---|
| **File** | `src/workflow/nodes/generate_test.py` |
| **Phase** | 5 — Worker Loop |
| **Uses LLM?** | Yes |
| **Signature** | `def generate_test(state: QAState) -> dict` |

**Purpose:** Generates test code for current file. Has two modes — fresh generation and self-heal fix.

**Reads from state:**
- `current_file`
- `workspace_path`
- `project_analysis` — specifically: `test_lib_config.framework_hints`, `module_system`, `path_aliases`, `uses_typescript`
- `retry_count` — if > 0, read `last_error` for fix mode
- `last_error` — only in retry mode
- `generated_test_code` — previous failing code, only in retry mode

**Returns to state:**
- `current_test_path` — path to written test file
- `generated_test_code` — the test source code

**Logic:**
- Read source code of `current_file`
- **If `retry_count == 0` (fresh):** build prompt with source + framework hints
- **If `retry_count > 0` (retry):** build prompt with source + previous test + error output
- Call LLM to generate/fix test
- Write test to `tests/` preserving directory structure
- Return test path and code

**Next:** → `run_test`

---

### Node 7: `run_test`
| | |
|---|---|
| **File** | `src/workflow/nodes/run_test.py` |
| **Phase** | 5 — Worker Loop |
| **Uses LLM?** | No |
| **Signature** | `def run_test(state: QAState) -> dict` |

**Purpose:** Executes test inside persistent container, captures result, decides PASS/RETRY/FAILED.

**Reads from state:**
- `container_id`
- `current_test_path`
- `current_file`
- `project_analysis` — specifically: `test_lib_config.per_file_test_cmd`, `test_lib_config.test_timeout`
- `retry_count`
- `max_retries`

**Returns to state:**
- `test_result` — `"PASS"` | `"RETRY"` | `"FAILED"`
- `retry_count` — incremented or reset
- `last_error` — stderr output (for retry)
- `test_output` — full terminal output
- Updated `file_statuses` — COMPLETED or FAILED
- Updated `todo_list` — mark file done

**Logic:**
- Format test command: `test_lib_config.per_file_test_cmd` with `{test_path}`
- Execute via `sandbox.exec_command(container_id, command)`
- If exit_code == 0 → `test_result = "PASS"`, mark COMPLETED
- If exit_code != 0 and `retry_count < max_retries` → `test_result = "RETRY"`, store `last_error`
- If exit_code != 0 and `retry_count >= max_retries` → `test_result = "FAILED"`, mark FAILED

**Next:** → `after_run_test` (router R3)

---

### Node 8: `generate_report`
| | |
|---|---|
| **File** | `src/workflow/nodes/generate_report.py` |
| **Phase** | 6 — Finalization |
| **Uses LLM?** | No |
| **Signature** | `def generate_report(state: QAState) -> dict` |

**Purpose:** Compiles final summary of entire QA run.

**Reads from state:**
- `file_statuses`
- `todo_list`
- `skipped_files`
- `discovered_files`
- `project_analysis.test_lib`
- `project_analysis.test_lib_config.name`

**Returns to state:**
- `final_report` — dict with all statistics

**Logic:**
- Count totals: discovered, tested, passed, failed, skipped
- Per-file breakdown with retry counts
- Display Rich table
- Optionally write JSON report

**Next:** → `teardown`

---

### Node 9: `teardown`
| | |
|---|---|
| **File** | `src/workflow/nodes/teardown.py` |
| **Phase** | 6 — Finalization |
| **Uses LLM?** | No |
| **Signature** | `def teardown(state: QAState) -> dict` |

**Purpose:** Stops and removes Docker container, optionally cleans workspace.

**Reads from state:**
- `container_id`
- `workspace_path`

**Returns to state:**
- (cleanup confirmation)

**Logic:**
- If container exists → stop, force remove
- Optional: clean `.temp/qa-agent-{uuid}` directory

**Next:** → END

---

## Conditional Routers (3)

### Router R1: `after_plan`
| | |
|---|---|
| **Location** | `src/workflow/graph.py` |
| **Function** | `def after_plan(state: QAState) -> str` |
| **Triggered after** | `plan_strategy` |

**Decision:**
| Condition | Return | Goes To |
|-----------|--------|---------|
| `todo_list` has PENDING items | `"init_docker"` | `init_docker` |
| `todo_list` is empty | `"generate_report"` | `generate_report` |

---

### Router R2: `after_select_next`
| | |
|---|---|
| **Location** | `src/workflow/graph.py` |
| **Function** | `def after_select_next(state: QAState) -> str` |
| **Triggered after** | `select_next_file` |

**Decision:**
| Condition | Return | Goes To |
|-----------|--------|---------|
| `current_file` is not `None` | `"generate_test"` | `generate_test` |
| `current_file` is `None` | `"generate_report"` | `generate_report` |

---

### Router R3: `after_run_test`
| | |
|---|---|
| **Location** | `src/workflow/graph.py` |
| **Function** | `def after_run_test(state: QAState) -> str` |
| **Triggered after** | `run_test` |

**Decision:**
| Condition | Return | Goes To |
|-----------|--------|---------|
| `test_result == "PASS"` | `"select_next_file"` | `select_next_file` (next file) |
| `test_result == "FAILED"` | `"select_next_file"` | `select_next_file` (gave up) |
| `test_result == "RETRY"` | `"generate_test"` | `generate_test` (self-heal loop) |

---

## Files to Update

| File | Action |
|------|--------|
| `src/workflow/state.py` | Add `ProjectAnalysis`, `TestLibConfig` TypedDicts. Add `workspace_path`, `project_analysis`, `test_result`, `last_error`, `retry_count`, `current_test_path`, `skipped_files` fields |
| `src/workflow/nodes/extract_files.py` | **CREATE** |
| `src/workflow/nodes/analyze_test_lib.py` | **CREATE** |
| `src/workflow/nodes/plan_strategy.py` | **CREATE** |
| `src/workflow/nodes/init_docker.py` | **CREATE** |
| `src/workflow/nodes/select_next_file.py` | **CREATE** |
| `src/workflow/nodes/generate_test.py` | **CREATE** |
| `src/workflow/nodes/run_test.py` | **CREATE** |
| `src/workflow/nodes/generate_report.py` | **CREATE** |
| `src/workflow/nodes/teardown.py` | **CREATE** |
| `src/workflow/graph.py` | **CREATE** — StateGraph + 3 conditional edges |
| `src/workflow/nodes/__init__.py` | **UPDATE** — add all exports |
| `src/workflow/__init__.py` | **UPDATE** — add graph exports |
| `src/utils/prompts.py` | **CREATE** — build prompts for plan, generate, fix |
| `src/utils/paths.py` | **CREATE** — path validation, repo clone |
| `src/utils/sandbox.py` | **UPDATE** — add 3 methods for persistent container |
| `src/main.py` | **CREATE** — CLI entry |
| `src/constants/languages/javascript.py` | **REFACTOR** — restructure to `available_test_libs` catalog |
| `src/constants/languages/typescript.py` | **REFACTOR** — same as above |
| `src/constants/languages/config.py` | **UPDATE** — add helper functions |

---

## Quick Summary Card

| # | Node | Phase | LLM | Next |
|---|------|-------|-----|------|
| 1 | `extract_files` | Ingest | No | → `analyze_test_lib` |
| 2 | `analyze_test_lib` | Analyze | No | → `plan_strategy` |
| 3 | `plan_strategy` | Plan | Yes | → **R1** |
| **R1** | `after_plan` | Router | — | → `init_docker` or `generate_report` |
| 4 | `init_docker` | Env | No | → `select_next_file` |
| 5 | `select_next_file` | Loop | No | → **R2** |
| **R2** | `after_select_next` | Router | — | → `generate_test` or `generate_report` |
| 6 | `generate_test` | Loop | Yes | → `run_test` |
| 7 | `run_test` | Loop | No | → **R3** |
| **R3** | `after_run_test` | Router | — | → `select_next_file` or `generate_test` |
| 8 | `generate_report` | Final | No | → `teardown` |
| 9 | `teardown` | Final | No | → END |

---
