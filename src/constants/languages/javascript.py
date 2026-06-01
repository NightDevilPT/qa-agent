"""JavaScript configuration profile."""

JAVASCRIPT_CONFIG = {
    "name": "javascript",
    "extensions": [".js", ".jsx", ".cjs", ".mjs"],
    # Added for Phase 3 (Plan Strategy) to filter out existing tests/configs
    "test_patterns": [".test.js", ".spec.js", ".test.jsx", ".spec.jsx", "config.js"],
    "exclude_patterns": [
        ".git/", "node_modules/", "dist/", "build/", "coverage/", 
        ".next/", "out/", "__tests__/", "**/*.test.*", "**/*.spec.*",
        "jest.config.*", "vite.config.*", "webpack.config.*", "rollup.config.*"
    ],
    # Future-proofing for Phase 2:
    "default_test_framework": "jest",
    "supported_frameworks": ["jest", "vitest", "mocha"]
}