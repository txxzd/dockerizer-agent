from pathlib import Path

from google.genai import types


class ToolExecutor:
    """Executes tools within a sandboxed project directory."""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root).resolve()

    def _validate_path(self, path: str) -> tuple[Path, dict | None]:
        """Validate that a path is within the project root. Returns (resolved_path, error_or_none)."""
        target = (self.project_root / path).resolve()
        if not str(target).startswith(str(self.project_root)):
            return target, {"error": "Path outside project directory"}
        return target, None

    def list_directory(self, path: str = ".") -> dict:
        """List files and directories at a path."""
        target, error = self._validate_path(path)
        if error:
            return error

        if not target.exists():
            return {"error": f"Directory not found: {path}"}
        if not target.is_dir():
            return {"error": f"Not a directory: {path}"}

        entries = []
        try:
            for item in target.iterdir():
                entries.append({"name": item.name, "type": "dir" if item.is_dir() else "file"})
        except PermissionError:
            return {"error": f"Permission denied: {path}"}

        # Sort: directories first, then files, alphabetically
        return {"entries": sorted(entries, key=lambda x: (x["type"] == "file", x["name"]))}

    def read_file(self, path: str, max_lines: int = 200) -> dict:
        """Read file contents."""
        target, error = self._validate_path(path)
        if error:
            return error

        if not target.exists():
            return {"error": f"File not found: {path}"}
        if not target.is_file():
            return {"error": f"Not a file: {path}"}

        try:
            content = target.read_text()
            lines = content.splitlines()
            truncated = len(lines) > max_lines
            if truncated:
                lines = lines[:max_lines]
            return {"content": "\n".join(lines), "truncated": truncated}
        except PermissionError:
            return {"error": f"Permission denied: {path}"}
        except UnicodeDecodeError:
            return {"error": f"Cannot read binary file: {path}"}

    def check_file_exists(self, path: str) -> dict:
        """Check if a file or directory exists."""
        target, error = self._validate_path(path)
        if error:
            return error

        return {
            "exists": target.exists(),
            "is_file": target.is_file() if target.exists() else False,
            "is_dir": target.is_dir() if target.exists() else False,
        }

    def write_dockerfile(self, content: str) -> dict:
        """Write the Dockerfile to the project root."""
        dockerfile_path = self.project_root / "Dockerfile"
        try:
            dockerfile_path.write_text(content if content.endswith("\n") else content + "\n")
            return {"success": True, "path": str(dockerfile_path)}
        except PermissionError:
            return {"error": "Permission denied writing Dockerfile"}


# Gemini FunctionDeclarations
TOOL_DECLARATIONS = [
    types.FunctionDeclaration(
        name="list_directory",
        description="List files and subdirectories in the given path. Use '.' for project root.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from project root (use '.' for root)",
                }
            },
            "required": ["path"],
        },
    ),
    types.FunctionDeclaration(
        name="read_file",
        description="Read the contents of a file. Use for package.json, requirements.txt, go.mod, Cargo.toml, etc.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to the file",
                },
                "max_lines": {
                    "type": "integer",
                    "description": "Maximum lines to read (default 200)",
                },
            },
            "required": ["path"],
        },
    ),
    types.FunctionDeclaration(
        name="check_file_exists",
        description="Check if a file or directory exists at the given path.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path to check",
                }
            },
            "required": ["path"],
        },
    ),
    types.FunctionDeclaration(
        name="write_dockerfile",
        description="Write the final Dockerfile to the project root. Call this when you have gathered enough information about the project.",
        parameters_json_schema={
            "type": "object",
            "properties": {
                "content": {
                    "type": "string",
                    "description": "Complete Dockerfile content",
                }
            },
            "required": ["content"],
        },
    ),
]
