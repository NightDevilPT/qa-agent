"""TypeScript configuration profile."""

TYPESCRIPT_CONFIG = {
    "name": "typescript",
    "extensions": [".ts", ".tsx", ".cts", ".mts"],
    "exclude_patterns": [
        ".git/", "node_modules/", "dist/", "build/", "coverage/", 
        ".next/", "out/", "__tests__/", "**/*.test.*", "**/*.spec.*",
        "jest.config.*", "vite.config.*", "tsconfig.*", "tsup.config.*"
    ],
    # Future-proofing for Phase 2:
    "default_test_framework": "jest",
    "supported_frameworks": ["jest", "vitest"]
}