import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
import fnmatch


@dataclass
class ProjectContext:
    root_path: str
    file_tree: list[str]
    config_files: dict[str, str]
    total_files: int
    extensions: dict[str, int]


CONFIG_FILES = [
    "package.json",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "requirements.txt",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Pipfile",
    "Pipfile.lock",
    "go.mod",
    "go.sum",
    "Cargo.toml",
    "Cargo.lock",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    "Gemfile",
    "Gemfile.lock",
    "composer.json",
    "composer.lock",
    "Makefile",
    "CMakeLists.txt",
    "Dockerfile",
    ".dockerignore",
    ".gitignore",
    "tsconfig.json",
    "vite.config.js",
    "vite.config.ts",
    "webpack.config.js",
    "next.config.js",
    "nuxt.config.js",
    "angular.json",
]

MAX_FILE_SIZE = 100_000  # 100KB limit for config file content


class ProjectAnalyzer:
    def __init__(self, project_path: str):
        self.project_path = Path(project_path).resolve()
        self._ignore_patterns: list[str] = []

    def _load_ignore_patterns(self) -> list[str]:
        patterns = [
            ".git",
            ".git/*",
            "__pycache__",
            "__pycache__/*",
            "node_modules",
            "node_modules/*",
            ".venv",
            ".venv/*",
            "venv",
            "venv/*",
            ".env",
            "*.pyc",
            "*.pyo",
            ".DS_Store",
            "*.log",
            "dist",
            "dist/*",
            "build",
            "build/*",
            "target",
            "target/*",
        ]

        for ignore_file in [".gitignore", ".dockerignore"]:
            ignore_path = self.project_path / ignore_file
            if ignore_path.exists():
                try:
                    content = ignore_path.read_text()
                    for line in content.splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            patterns.append(line)
                except Exception:
                    pass

        return patterns

    def _should_ignore(self, rel_path: str) -> bool:
        for pattern in self._ignore_patterns:
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            if fnmatch.fnmatch(os.path.basename(rel_path), pattern):
                return True
        return False

    def _collect_file_tree(self) -> tuple[list[str], dict[str, int]]:
        file_tree = []
        extensions: dict[str, int] = {}

        for root, dirs, files in os.walk(self.project_path):
            rel_root = os.path.relpath(root, self.project_path)
            if rel_root == ".":
                rel_root = ""

            dirs[:] = [
                d for d in dirs
                if not self._should_ignore(os.path.join(rel_root, d) if rel_root else d)
            ]

            for file in files:
                rel_path = os.path.join(rel_root, file) if rel_root else file
                if self._should_ignore(rel_path):
                    continue

                file_tree.append(rel_path)
                ext = Path(file).suffix.lower()
                if ext:
                    extensions[ext] = extensions.get(ext, 0) + 1

        return sorted(file_tree), extensions

    def _read_config_files(self, file_tree: list[str]) -> dict[str, str]:
        config_contents: dict[str, str] = {}

        for filename in CONFIG_FILES:
            if filename in file_tree:
                file_path = self.project_path / filename
                try:
                    if file_path.stat().st_size <= MAX_FILE_SIZE:
                        config_contents[filename] = file_path.read_text()
                except Exception:
                    pass

        return config_contents

    def analyze(self) -> ProjectContext:
        if not self.project_path.exists():
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")

        if not self.project_path.is_dir():
            raise NotADirectoryError(f"Project path is not a directory: {self.project_path}")

        self._ignore_patterns = self._load_ignore_patterns()
        file_tree, extensions = self._collect_file_tree()
        config_files = self._read_config_files(file_tree)

        return ProjectContext(
            root_path=str(self.project_path),
            file_tree=file_tree,
            config_files=config_files,
            total_files=len(file_tree),
            extensions=extensions,
        )
