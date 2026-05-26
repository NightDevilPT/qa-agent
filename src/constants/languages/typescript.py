"""
TypeScript Language Configuration
==================================
"""

import json

TYPESCRIPT_CONFIG = {
    "name": "TypeScript",
    "image": "node:20-alpine",
    "extensions": [".ts", ".tsx"],
    "install_cmd": "npm install",
    "test_cmd": "npx jest --json 2>&1",
    "test_file_pattern": "{name}.test.ts",
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
            "scripts": {"test": "jest"},
            "devDependencies": {
                "jest": "^29.0.0",
                "typescript": "^5.0.0",
                "ts-jest": "^29.0.0",
                "@types/jest": "^29.0.0",
            },
        }, indent=2),
        "jest.config.js": (
            "export default {\n"
            "  preset: 'ts-jest',\n"
            "  testEnvironment: 'node',\n"
            "  transform: {\n"
            "    '^.+\\\\.tsx?$': 'ts-jest',\n"
            "  },\n"
            "  testMatch: ['**/*.test.ts', '**/*.spec.ts'],\n"
            "  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],\n"
            "  injectGlobals: false,\n"
            "};\n"
        ),
        "tsconfig.json": json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "ESNext",
                "moduleResolution": "node",
                "esModuleInterop": True,
                "strict": True,
                "skipLibCheck": True,
                "types": ["jest"],
            },
            "include": ["src/**/*", "tests/**/*"],
        }, indent=2),
    },
}