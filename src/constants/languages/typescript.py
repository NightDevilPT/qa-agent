"""TypeScript configuration profile."""

TYPESCRIPT_CONFIG = {
    "name": "typescript",
    # Added JS extensions here because TS projects often contain JS/JSX files
    "extensions": [".ts", ".tsx", ".cts", ".mts", ".js", ".jsx", ".cjs", ".mjs"],
    # Added for Phase 3 (Plan Strategy) to filter out existing tests/configs
    "test_patterns": [".test.ts", ".spec.ts", ".test.tsx", ".spec.tsx", "d.ts", "config.ts", "config.js"],
    "exclude_patterns": [
        ".git/", "node_modules/", "dist/", "build/", "coverage/", 
        ".next/", "out/", "__tests__/", "**/*.test.*", "**/*.spec.*",
        "jest.config.*", "vite.config.*", "tsconfig.*", "tsup.config.*"
    ],
    # Future-proofing for Phase 2:
    "default_test_framework": "jest",
    "supported_frameworks": ["jest", "vitest"]
}