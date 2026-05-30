import json

TYPESCRIPT_CONFIG = {
    "name": "TypeScript",
    "image": "node:20-alpine",
    "extensions": [".ts", ".tsx"],
    # pathspec / .gitignore-style patterns — used by extract_files
    "exclude_patterns": [
        ".git/",
        "node_modules/",
        "dist/",
        "build/",
        "coverage/",
        ".next/",
        ".nuxt/",
        "out/",
        "__tests__/",
        "**/*.test.ts",
        "**/*.test.tsx",
        "**/*.spec.ts",
        "**/*.spec.tsx",
        "**/*.d.ts",
        "**/*.min.js",
        "**/jest.config.js",
        "**/jest.setup.js",
        "**/tsconfig.json",
        "**/tsconfig.*.json",
        "**/babel.config.js",
        "**/webpack.config.js",
        "**/vite.config.ts",
        "**/vite.config.js",
    ],
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
            "name": "qa-test-ts",
            "version": "1.0.0",
            "private": True,
            "scripts": {"test": "jest"},
            "devDependencies": {
                "jest": "^29.7.0",
                "typescript": "^5.3.3",
                "ts-jest": "^29.1.1",
                "@types/jest": "^29.5.11",
            },
        }, indent=2),
        "jest.config.js": (
            "module.exports = {\n"
            "  preset: 'ts-jest',\n"
            "  testEnvironment: 'node',\n"
            "  testMatch: ['**/*.test.ts', '**/*.spec.ts'],\n"
            "  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],\n"
            "};\n"
        ),
        "tsconfig.json": json.dumps({
            "compilerOptions": {
                "target": "ES2020",
                "module": "CommonJS",
                "moduleResolution": "node",
                "esModuleInterop": True,
                "strict": True,
                "skipLibCheck": True,
                "forceConsistentCasingInFileNames": True,
                "types": ["jest"],
            },
            "include": ["src/**/*", "tests/**/*", "**/*"],
        }, indent=2),
    },
}