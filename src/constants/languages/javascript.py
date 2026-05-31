"""JavaScript configuration profile."""

JAVASCRIPT_CONFIG = {
    "name": "javascript",
    "extensions": [".js", ".jsx", ".cjs", ".mjs"],
    "exclude_patterns": [
        ".git/", "node_modules/", "dist/", "build/", "coverage/", 
        ".next/", "out/", "__tests__/", "**/*.test.*", "**/*.spec.*",
        "jest.config.*", "vite.config.*", "webpack.config.*", "rollup.config.*"
    ],
    # Future-proofing for Phase 2:
    "default_test_framework": "jest",
    "supported_frameworks": ["jest", "vitest", "mocha"]
}