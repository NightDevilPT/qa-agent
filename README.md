## QA Agent - Project Requirements

---

### What We Need

Build an autonomous AI agent that generates and runs test cases for JavaScript and TypeScript code.

---

### Input

User passes one of these through CLI:

- A file path (`src/utils.ts`)
- A folder path (`./my-project/`)
- A GitHub repo URL (`https://github.com/user/repo`)

---

### Agent Flow

```
1. EXECUTION starts
2. User selects input type: repo, folder, or file
3. Read all files from the selected source
4. Manage state for each file (track progress)
5. Generate test cases using LLM
6. Run test cases in Docker container
7. If PASSED → move to next file
8. If FAILED → pass error and code back to LLM to re-generate
9. Run again
10. If still FAILED after max retries → log failure and move to next file
11. Repeat until all files processed
```

---

### Supported Languages

- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)

---

### Current Scope

- CLI-based only, no CI/CD integration yet
- Local Docker LLM for test generation
- Docker containers for isolated test execution
- Jest as the test framework
- Self-healing retry loop for failed tests
- Human-in-the-loop approval at key steps

---

### What To Build Now

1. CLI that accepts file/folder/repo input
2. File reader and analyzer
3. LLM integration for test generation
4. Docker sandbox for test execution
5. Retry loop for fixing failed tests
6. State management per file
7. Output generated test files to disk