import os
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agent_deployer.analyzer import ProjectContext

load_dotenv()


SYSTEM_PROMPT = """You are an expert at creating Dockerfiles for containerizing applications.

Given a project's file structure and configuration files, generate an optimal Dockerfile.

Follow these best practices:
1. Use minimal base images (alpine variants when possible)
2. Multi-stage builds: ONLY use for compiled languages (Go, Rust, Java, C/C++) where you copy a binary.
   - For interpreted languages (Python, Node.js, Ruby): use single-stage builds because pip/npm packages
     install to system directories that won't be copied with just "COPY --from=builder /app ."
   - If using multi-stage for Python, you must copy the entire site-packages directory
3. Run as non-root user for security (create user before switching)
4. Order layers for optimal caching: copy dependency files first, install, then copy source
5. Use .dockerignore patterns implicitly (don't COPY unnecessary files)
6. Set appropriate WORKDIR
7. Expose relevant ports based on the application type
8. Use CMD for the main command (not ENTRYPOINT unless wrapping a specific binary)
9. Health checks: use wget or curl depending on what's available in the base image
   - Alpine images have wget by default, not curl
10. Pin base image versions for reproducibility

Output ONLY the Dockerfile content, no explanations or markdown formatting.
Do not wrap in code blocks. Just raw Dockerfile content."""


class DockerfileAgent:
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it as an environment variable or pass it directly."
            )
        self.client = genai.Client(api_key=self.api_key)

    def _build_prompt(self, context: ProjectContext) -> str:
        prompt_parts = [
            "Analyze this project and generate an appropriate Dockerfile.\n",
            f"Project root: {context.root_path}\n",
            f"Total files: {context.total_files}\n",
            "\n## File Extensions (count):\n",
        ]

        for ext, count in sorted(context.extensions.items(), key=lambda x: -x[1]):
            prompt_parts.append(f"  {ext}: {count}\n")

        prompt_parts.append("\n## File Tree:\n")
        for file in context.file_tree[:200]:
            prompt_parts.append(f"  {file}\n")

        if len(context.file_tree) > 200:
            prompt_parts.append(f"  ... and {len(context.file_tree) - 200} more files\n")

        prompt_parts.append("\n## Configuration Files:\n")
        for filename, content in context.config_files.items():
            truncated = content[:5000] if len(content) > 5000 else content
            prompt_parts.append(f"\n### {filename}:\n```\n{truncated}\n```\n")

        return "".join(prompt_parts)

    def generate_dockerfile(self, context: ProjectContext) -> str:
        prompt = self._build_prompt(context)

        response = self.client.models.generate_content(
            model="gemini-2.0-flash",
            contents=SYSTEM_PROMPT + "\n\n" + prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=2048,
            ),
        )

        dockerfile_content = response.text.strip()

        if dockerfile_content.startswith("```"):
            lines = dockerfile_content.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            dockerfile_content = "\n".join(lines)

        return dockerfile_content

    def generate_and_save(
        self, context: ProjectContext, output_path: Optional[str] = None
    ) -> str:
        dockerfile_content = self.generate_dockerfile(context)

        if output_path is None:
            output_path = os.path.join(context.root_path, "Dockerfile")

        with open(output_path, "w") as f:
            f.write(dockerfile_content)
            if not dockerfile_content.endswith("\n"):
                f.write("\n")

        return output_path
