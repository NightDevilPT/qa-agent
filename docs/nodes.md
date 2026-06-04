Here is the fully updated `nodes.md` file reflecting your exact current LangGraph implementation and file structure.

---

# Complete Nodes List — What We Have Built

---

## Total: 11 Action Nodes + 2 Conditional Routers = 13 Components

---

## Action Nodes (11)

### Node 1: `clone_files`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/clone_files.py` |
| **Phase** | 1 — Ingestion & Extraction |
| **Uses LLM?** | No |
| **Signature** | `def clone_files(state: QAState) -> dict` |

**Purpose:** Handles input processing (file, folder, or repo), generates a unique workspace ID, and securely copies/clones the project into the `.temp/qa-agent-{uuid}` directory.

**Reads from state:**

* `target_path` / `repo_url`
* `input_type` (`"file"`, `"folder"`, `"repo"`)
* `project_language`

**Returns to state:**

* `workspace_root` — Absolute path to the isolated working directory.

**Next:** → `discover_files`

---

### Node 2: `discover_files`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/discover_files.py` |
| **Phase** | 1 — File Discovery |
| **Uses LLM?** | No |
| **Signature** | `def discover_files(state: QAState) -> dict` |

**Purpose:** Scans the `workspace_root` to find all available files. Filters out build artifacts, `node_modules`, and existing test files based on exclusion patterns.

**Reads from state:**

* `workspace_root`
* `project_language`

**Returns to state:**

* `file_to_be_process` — List of all potentially relevant relative file paths.

**Next:** → `analyze_project`

---

### Node 3: `analyze_project`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/analyze_project.py` |
| **Phase** | 2 — Project Analysis |
| **Uses LLM?** | Yes — with structured output (`SetupFilesOutput`, `ProjectAnalysisOutput`) |
| **Signature** | `def analyze_project(state: QAState) -> dict` |

**Purpose:** A 2-step LLM extraction process. Step 1 finds setup files (like `package.json`). Step 2 reads them to detect the test framework, module system, and configurations.

**Reads from state:**

* `workspace_root`
* `file_to_be_process`
* `project_language`

**Returns to state:**

* `project_analysis` — Dictionary containing `test_lib`, `module_system`, `project_dependencies`, and `test_lib_config` (install/test commands).
* Token usage tracking.

**Next:** → `plan_strategy`

---

### Node 4: `plan_strategy`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/plan_strategy.py` |
| **Phase** | 3 — Planning |
| **Uses LLM?** | Yes — with structured output (`Step1CandidateFiles`, `Step2FileAnalysis`) |
| **Signature** | `def plan_strategy(state: QAState) -> dict` |

**Purpose:** AI filters out boilerplate, reads remaining files to map internal dependencies, and performs a topological sort so zero-dependency files are tested first.

**Reads from state:**

* `workspace_root`
* `file_to_be_process`

**Returns to state:**

* `todo_list` — Priority-ordered list of files to test.
* `dependency_graph` — Map of file imports.
* `file_statuses` — Initialized ledger for tracking completion and retries.
* Token usage tracking.

**Next:** → `setup_sandbox`

---

### Node 5: `setup_sandbox`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/setup_sandbox.py` |
| **Phase** | 4 — Environment Preparation |
| **Uses LLM?** | No |
| **Signature** | `def setup_sandbox(state: QAState) -> dict` |

**Purpose:** Initializes the persistent Docker container (`node:20-alpine`), writes framework config files, and runs `npm install`.

**Reads from state:**

* `workspace_root`
* `project_language`
* `project_analysis`

**Returns to state:**

* `sandbox_ready` — Boolean indicating successful setup.

**Next:** → `select_next_file`

---

### Node 6: `select_next_file`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/select_next_file.py` |
| **Phase** | 5 — Worker Loop |
| **Uses LLM?** | No |
| **Signature** | `def select_next_file(state: QAState) -> dict` |

**Purpose:** Queue manager that pops the next `pending` file from the `todo_list`, reads its source code, and sets it as the active item.

**Reads from state:**

* `todo_list`
* `file_statuses`
* `workspace_root`

**Returns to state:**

* `current_status` — Resets active tracking (`current_file`, `current_source_code`, `retries`).
* `file_statuses` — Updates target file to `in_progress`.

**Next:** → `route_after_select` (Router R1)

---

### Node 7: `identify_edge_cases`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/identify_edge_cases.py` |
| **Phase** | 5 — Worker Loop (Pre-Generation) |
| **Uses LLM?** | Yes — with structured output (`EdgeCasePlan`) |
| **Signature** | `def identify_edge_cases(state: QAState) -> dict` |

**Purpose:** Analyzes the active file's source code and explicitly writes a checklist of happy paths, edge cases, and error handling scenarios to test. Skipped during retry loops.

**Reads from state:**

* `current_status`
* `file_statuses`

**Returns to state:**

* Updated `current_status` — Injects `target_edge_cases`.
* Updated `file_statuses` — Appends edge cases to the ledger.
* Token usage tracking.

**Next:** → `generate_test`

---

### Node 8: `generate_test`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/generate_test.py` |
| **Phase** | 5 — Worker Loop |
| **Uses LLM?** | Yes |
| **Signature** | `def generate_test(state: QAState) -> dict` |

**Purpose:** Writes or fixes the unit test. Injects calculated relative import paths, dependency context, and the required edge case checklist. During retries, it uses the targeted error log to self-heal.

**Reads from state:**

* `current_status`
* `file_statuses`
* `dependency_graph`
* `project_analysis`
* `workspace_root`

**Returns to state:**

* `file_statuses` — Updates `test_file_path` and token consumption.
* Token usage tracking.
* *(Writes actual file to the Docker workspace)*

**Next:** → `execute_test`

---

### Node 9: `execute_test`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/execute_test.py` |
| **Phase** | 5 — Worker Loop |
| **Uses LLM?** | Yes — with structured output for error parsing (`TestParserOutput`) |
| **Signature** | `def execute_test(state: QAState) -> dict` |

**Purpose:** Runs the test inside the Docker sandbox. If tests fail, it uses an LLM to parse the terminal output and extract exactly *which* scenarios failed, creating a focused error report. Updates the edge case ledger.

**Reads from state:**

* `workspace_root`
* `project_analysis`
* `current_status`
* `file_statuses`
* `max_retries`

**Returns to state:**

* Updated `current_status` — `test_passed`, `retries`, `error_log` (Targeted report).
* Updated `file_statuses` — Marks edge cases as passed/failed.
* Token usage tracking.

**Next:** → `route_after_execute` (Router R2)

---

### Node 10: `generate_report`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/generate_report.py` |
| **Phase** | 6 — Finalization |
| **Uses LLM?** | No |
| **Signature** | `def generate_report(state: QAState) -> dict` |

**Purpose:** Compiles a final terminal string summarizing the run: total files, pass/fail rates, retries, and overall token usage.

**Reads from state:**

* `file_statuses`
* `total_tokens`
* `project_analysis`

**Returns to state:**

* `final_report` — The formatted string.

**Next:** → `teardown`

---

### Node 11: `teardown`

|  |  |
| --- | --- |
| **File** | `src/workflow/nodes/teardown.py` |
| **Phase** | 6 — Finalization |
| **Uses LLM?** | No |
| **Signature** | `def teardown(state: QAState) -> dict` |

**Purpose:** Safely shuts down and removes the persistent Docker container environment.

**Reads from state:**

* `container_id`

**Returns to state:**

* `container_id` — `None`
* `sandbox_ready` — `False`

**Next:** → END

---

## Conditional Routers (2)

### Router R1: `route_after_select`

|  |  |
| --- | --- |
| **Location** | `src/workflow/graph.py` |
| **Triggered after** | `select_next_file` |

**Decision:**

| Condition | Return | Goes To |
| --- | --- | --- |
| `current_file` is NOT `None` | `"identify_edge_cases"` | `identify_edge_cases` (Queue has files) |
| `current_file` is `None` | `"generate_report"` | `generate_report` (Queue is empty) |

---

### Router R2: `route_after_execute`

|  |  |
| --- | --- |
| **Location** | `src/workflow/graph.py` |
| **Triggered after** | `execute_test` |

**Decision:**

| Condition | Return | Goes To |
| --- | --- | --- |
| `passed` == True | `"select_next_file"` | `select_next_file` (Success) |
| `passed` == False AND `retries < max_retries` | `"generate_test"` | `generate_test` (Self-Heal Loop) |
| `passed` == False AND `retries >= max_retries` | `"select_next_file"` | `select_next_file` (Permanent Fail) |

---

## Quick Summary Card

| # | Node | Phase | LLM | Next |
| --- | --- | --- | --- | --- |
| 1 | `clone_files` | Ingest | No | → `discover_files` |
| 2 | `discover_files` | Discover | No | → `analyze_project` |
| 3 | `analyze_project` | Analyze | **Yes** | → `plan_strategy` |
| 4 | `plan_strategy` | Plan | **Yes** | → `setup_sandbox` |
| 5 | `setup_sandbox` | Env | No | → `select_next_file` |
| 6 | `select_next_file` | Loop | No | → **R1** |
| **R1** | `route_after_select` | Router | — | → `identify_edge_cases` or `generate_report` |
| 7 | `identify_edge_cases` | Loop | **Yes** | → `generate_test` |
| 8 | `generate_test` | Loop | **Yes** | → `execute_test` |
| 9 | `execute_test` | Loop | **Yes** | → **R2** |
| **R2** | `route_after_execute` | Router | — | → `select_next_file` or `generate_test` |
| 10 | `generate_report` | Final | No | → `teardown` |
| 11 | `teardown` | Final | No | → END |