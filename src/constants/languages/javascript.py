"""
JavaScript Language Configuration
==================================
"""

import json

JAVASCRIPT_CONFIG = {
    "name": "JavaScript",
    "image": "node:20-alpine",
    "extensions": [".js", ".jsx"],
    "install_cmd": "npm install",
    "test_cmd": "npx jest --json 2>&1",
    "test_file_pattern": "{name}.test.js",
    "workspace_structure": {
        "file": {
            "source_dir": "src",
            "test_dir": "tests",
            "mirror_structure": False,
        },
        "folder": {
            "source_dir": None,
            "test_dir": "tests",
            "mirror_structure": True,
        },
        "repo": {
            "source_dir": None,
            "test_dir": "tests",
            "mirror_structure": True,
        },
    },
    "config_files": {
        "package.json": json.dumps({
            "name": "qa-test",
            "version": "1.0.0",
            "private": True,
            "type": "module",
            "scripts": {"test": "jest"},
            "devDependencies": {"jest": "^29.0.0"},
        }, indent=2),
        "jest.config.js": (
            "export default {\n"
            "  testEnvironment: 'node',\n"
            "  transform: {},\n"
            "  testMatch: ['**/*.test.js', '**/*.spec.js'],\n"
            "  moduleFileExtensions: ['js', 'jsx', 'json', 'node'],\n"
            "  injectGlobals: false,\n"
            "};\n"
        ),
    },
}