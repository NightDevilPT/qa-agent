import json

JAVASCRIPT_CONFIG = {
    "name": "JavaScript",
    "image": "node:20-alpine",
    "extensions": [".js", ".jsx"],
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
        "**/*.test.js",
        "**/*.test.jsx",
        "**/*.spec.js",
        "**/*.spec.jsx",
        "**/*.min.js",
        "**/*.bundle.js",
        "**/jest.config.js",
        "**/jest.setup.js",
        "**/babel.config.js",
        "**/webpack.config.js",
        "**/rollup.config.js",
        "**/vite.config.js",
    ],
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
        # --- BABEL ADDED TO DEV DEPENDENCIES ---
        "package.json": json.dumps({
            "name": "qa-test",
            "version": "1.0.0",
            "private": True,
            "scripts": {"test": "jest"},
            "devDependencies": {
                "jest": "^29.7.0",
                "@babel/core": "^7.23.0",
                "@babel/preset-env": "^7.23.0"
            },
        }, indent=2),
        
        # --- JEST CONFIGURED TO USE BABEL ---
        "jest.config.js": (
            "module.exports = {\n"
            "  testEnvironment: 'node',\n"
            "  testMatch: ['**/*.test.js', '**/*.spec.js'],\n"
            "  moduleFileExtensions: ['js', 'jsx', 'json', 'node'],\n"
            "  transform: {\n"
            "    '^.+\\\\.jsx?$': 'babel-jest'\n"
            "  }\n"
            "};\n"
        ),
        
        # --- NEW FILE: BABEL CONFIG ---
        "babel.config.js": (
            "module.exports = {\n"
            "  presets: [['@babel/preset-env', {targets: {node: 'current'}}]],\n"
            "};\n"
        )
    },
}