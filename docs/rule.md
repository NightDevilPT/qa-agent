## QA Agent - Project Rulebook

---

### 1. Project Structure

```
qa-agents/
├── docs/
│   └── rule.md                  # This rulebook
├── examples/                    # Test files for internal testing
│   ├── single-file.js           # Single JS file for testing
│   ├── single-file.ts           # Single TS file for testing
│   └── full-project/            # Multi-file projects for testing
├── src/
│   ├── main.py                  # Entry point, execution flow
│   ├── middleware/               # LangChain agent middleware
│   │   ├── __init__.py           # Export all middleware
│   │   └── logger.py            # Logging middleware
│   ├── utils/                    # Utility functions
│   │   ├── __init__.py           # Export all utils
│   │   ├── hitl.py              # Human-in-the-loop prompts
│   │   ├── llm.py               # Docker LLM connection
│   │   └── paths.py             # Path resolution logic
│   ├── tools/                    # Agent tool definitions
│   │   ├── __init__.py           # Export all tools
│   │   └── ...                   # Add tools here
│   ├── constants/                # Configuration values only
│   │   └── languages/           # Language-specific configs
│   │       ├── __init__.py       # Export all language configs
│   │       ├── config.py         # Central hub, loads all languages
│   │       ├── typescript.py     # TypeScript config
│   │       └── javascript.py     # JavaScript config
│   └── __init__.py               # Package marker
├── pyproject.toml                # Dependencies
├── .env                          # Environment variables
└── README.md
```

---

### 2. Folder Rules

| Folder                 | Purpose                            | Rules                                                   |
| ---------------------- | ---------------------------------- | ------------------------------------------------------- |
| `docs/`                | Documentation                      | Project documentation and rulebook                      |
| `examples/`            | Test files for internal validation | Single files at root, multi-file projects in subfolders |
| `middleware/`          | LangChain agent middleware         | One file per middleware, export via `__init__.py`       |
| `utils/`               | Reusable utility functions         | One file per utility, export via `__init__.py`          |
| `tools/`               | Agent tool definitions             | One file per tool category, export via `__init__.py`    |
| `constants/languages/` | Language-specific configs          | One file per language, loaded by `config.py` hub        |

---

### 3. Import Rules

```python
# ✅ Correct
from utils.hitl import ask_human
from middleware.logger import create_logger_middleware
from tools.file_tools import create_file_tools
from constants.languages import get_language_config, detect_language

# ❌ Wrong
from src.utils.hitl import ask_human
```

---

### 4. `__init__.py` Rules

**Every folder must have `__init__.py` that exports all public functions.**

**When adding new files, update `__init__.py` immediately.**

```python
# tools/__init__.py
from tools.file_tools import create_file_tools
from tools.test_tools import create_test_tools

__all__ = ["create_file_tools", "create_test_tools"]
```

```python
# constants/languages/__init__.py
from constants.languages.config import (
    LANGUAGE_CONFIG,
    SUPPORTED_LANGUAGES,
    DEFAULT_LANGUAGE,
    get_language_config,
    detect_language,
)

__all__ = [
    "LANGUAGE_CONFIG",
    "SUPPORTED_LANGUAGES",
    "DEFAULT_LANGUAGE",
    "get_language_config",
    "detect_language",
]
```

---

### 5. Tools Rules

**All agent tools go in `tools/` folder.**

```
tools/
├── __init__.py          # Export all tools
└── ...                  # Add tool files here
```

---

### 6. Constants Rules

**Only language configs. Each language has its own file.**

```
constants/
└── languages/
    ├── __init__.py       # Export all language configs
    ├── config.py         # Central hub, loads all languages
    ├── typescript.py     # TypeScript config
    └── javascript.py     # JavaScript config
```

**Each language config contains:**

- `name` - Display name
- `image` - Docker image
- `extensions` - File extensions
- `install_cmd` - Dependency install command
- `test_cmd` - Test run command
- `test_file_pattern` - Test file naming pattern
- `workspace_structure` - Source/test directory layout
- `config_files` - Default config files (package.json, jest.config, etc.)

**Workspace structure per language:**

```python
"workspace_structure": {
    "file": {
        "source_dir": "src",       # Single file goes here
        "test_dir": "tests",        # Test file goes here
        "mirror_structure": False,  # Don't mirror original path
    },
    "folder": {
        "source_dir": None,         # Keep original structure
        "test_dir": "tests",        # Tests alongside mirrored structure
        "mirror_structure": True,   # Mirror original folder structure
    },
    "repo": {
        "source_dir": None,         # Keep original structure
        "test_dir": "tests",        # Tests alongside mirrored structure
        "mirror_structure": True,   # Mirror original repo structure
    },
}
```

---

### 7. Adding a New Language (Future)

**Step 1:** Create `constants/languages/python.py`:

```python
PYTHON_CONFIG = {
    "name": "Python",
    "image": "python:3.12-alpine",
    "extensions": [".py"],
    "install_cmd": "pip install pytest pytest-json-report",
    "test_cmd": "python -m pytest --json-report 2>&1",
    "test_file_pattern": "test_{name}.py",
    "workspace_structure": {
        "file": {"source_dir": "src", "test_dir": "tests", "mirror_structure": False},
        "folder": {"source_dir": None, "test_dir": "tests", "mirror_structure": True},
        "repo": {"source_dir": None, "test_dir": "tests", "mirror_structure": True},
    },
    "config_files": {},
}
```

**Step 2:** Update `constants/languages/config.py`:

```python
from constants.languages.python import PYTHON_CONFIG

LANGUAGE_CONFIG["python"] = PYTHON_CONFIG
SUPPORTED_LANGUAGES.append("python")
```

**No other files need changes. `main.py` and `utils` work without modification.**

---

### 8. `main.py` Rules

**The main execution flow:**

```
1. Ask user for input type (file/folder/repo)
2. Resolve path
3. Read all files
4. For each file:
   a. Generate test cases (LLM)
   b. Run tests (Docker sandbox)
   c. Passed → Next file
   d. Failed → Re-generate (max 3 retries)
        Passed → Next file
        Failed → Log & Next file
5. Done
```

---

### 9. Packages (DO NOT ADD MORE)

```
docker>=7.1.0
langchain>=1.3.1
langchain-community>=0.4.2
langchain-core>=1.4.0
langgraph>=1.2.1
langchain-openai>=1.2.2
httpx>=0.28.1
typer>=0.25.1
rich>=15.0.0
tree-sitter>=0.25.2
tree-sitter-javascript>=0.25.0
tree-sitter-typescript>=0.23.2
pydantic>=2.13.4
pydantic-settings>=2.14.1
gitpython>=3.1.50
pathspec>=1.1.1
sh>=2.2.2
```

**Only use these packages. No new packages allowed.**

---

### 10. Language Support

| Status      | Language   | Extensions    | Config File     |
| ----------- | ---------- | ------------- | --------------- |
| **Current** | JavaScript | `.js`, `.jsx` | `javascript.py` |
| **Current** | TypeScript | `.ts`, `.tsx` | `typescript.py` |
| _Future_    | Python     | `.py`         | `python.py`     |
| _Future_    | Rust       | `.rs`         | `rust.py`       |
| _Future_    | Go         | `.go`         | `go.py`         |

**To add a language: create a config file + register in `config.py`. Nothing else changes.**

---

### 11. SOLID Principles (MUST FOLLOW)

| Principle                     | Rule                                                           |
| ----------------------------- | -------------------------------------------------------------- |
| **S** - Single Responsibility | Each file/class/function does ONE thing only                   |
| **O** - Open/Closed           | Open for extension, closed for modification                    |
| **L** - Liskov Substitution   | Any implementation must work wherever its parent is used       |
| **I** - Interface Segregation | Keep interfaces small and focused                              |
| **D** - Dependency Inversion  | Depend on abstractions (configs), not concrete implementations |

**Practical Rules:**

- New language? → Add file in `constants/languages/`, update `config.py`. Don't touch `main.py`
- New tool? → Add file in `tools/`, don't modify existing tools
- New middleware? → Add file in `middleware/`, existing middleware unchanged
- New utility? → Add file in `utils/`, existing utils unchanged

---

### 12. Adaptive Design Rules

- **Configuration-driven**: Behavior changes via config, not code changes
- **Pluggable architecture**: Every component (language, tool, middleware) is a plugin
- **Backward compatible**: Old inputs and flows must always work
- **Loose coupling**: Components communicate through well-defined interfaces

---

### 13. Current Scope

- JavaScript (`.js`, `.jsx`) and TypeScript (`.ts`, `.tsx`)
- File and folder inputs (repo coming soon)
- Jest test framework
- Docker sandbox execution
- Local Docker LLM
- Self-healing retry loop
