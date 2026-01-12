import json
import os
from typing import Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

from agent_deployer.tools import TOOL_DECLARATIONS, ToolExecutor

load_dotenv()


SYSTEM_PROMPT = """You are an expert at creating Dockerfiles for containerizing applications.

You have tools to explore the project. Follow this process:
1. Call list_directory with path="." to see the project structure
2. Read key config files (package.json, requirements.txt, go.mod, Cargo.toml, etc.)
3. Check for existing Dockerfile or .dockerignore if needed
4. When you understand the project, call write_dockerfile with the complete Dockerfile

Rules for the Dockerfile:
- Only COPY files that actually exist in the project
- Use minimal base images (alpine variants when possible)
- Multi-stage builds ONLY for compiled languages (Go, Rust, Java, C/C++)
- For interpreted languages (Python, Node.js, Ruby): use single-stage builds
- Order layers for caching: copy dependency manifests first, install deps, then copy source
- Set a sensible WORKDIR (e.g., /app)
- Expose the correct port based on the project config
- Use CMD for the main process (avoid ENTRYPOINT unless strictly needed)
- Run as non-root user when practical
- Keep it simple and correct

Output ONLY the Dockerfile content when calling write_dockerfile, no markdown or explanations."""


class DockerfileAgent:
    """An agentic Dockerfile generator that explores projects using tools."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError(
                "GEMINI_API_KEY not found. Set it as an environment variable or pass it directly."
            )
        self.client = genai.Client(api_key=self.api_key)
        self.tools = types.Tool(function_declarations=TOOL_DECLARATIONS)

    def run(self, project_path: str, max_turns: int = 15, verbose: bool = True) -> str:
        """
        Run the agent loop until a Dockerfile is written.

        Args:
            project_path: Path to the project directory
            max_turns: Maximum number of agent turns before stopping
            verbose: Whether to print tool calls

        Returns:
            Path to the generated Dockerfile, or an error message
        """
        executor = ToolExecutor(project_path)

        contents = [
            types.Content(
                role="user",
                parts=[types.Part.from_text(text=f"Generate a Dockerfile for the project at: {project_path}")],
            )
        ]

        for _turn in range(max_turns):
            response = self.client.models.generate_content(
                model="gemini-2.5-flash",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_PROMPT,
                    tools=[self.tools],
                    temperature=0.2,
                ),
            )

            # Append assistant response to conversation
            contents.append(response.candidates[0].content)

            # Check for function calls
            if not response.function_calls:
                # No function call = agent is done or stuck
                return response.text or "Agent completed without writing Dockerfile"

            # Execute each function call
            function_response_parts = []
            for fc in response.function_calls:
                if verbose:
                    args_str = json.dumps(fc.args) if fc.args else "{}"
                    print(f"  [Tool] {fc.name}({args_str})")

                # Dispatch to executor
                handler = getattr(executor, fc.name, None)
                if handler:
                    # Filter args to only include expected parameters
                    result = handler(**fc.args)
                else:
                    result = {"error": f"Unknown tool: {fc.name}"}

                # Check if this is the terminal action
                if fc.name == "write_dockerfile" and result.get("success"):
                    return result["path"]

                function_response_parts.append(
                    types.Part.from_function_response(name=fc.name, response=result)
                )

            # Append function results to conversation
            contents.append(types.Content(role="user", parts=function_response_parts))

        return "Max turns reached without completing Dockerfile generation"
