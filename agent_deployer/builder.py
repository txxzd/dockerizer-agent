import subprocess
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable


@dataclass
class BuildResult:
    success: bool
    image_id: Optional[str]
    error: Optional[str]


class DockerBuilder:
    def __init__(self, context_path: str, dockerfile_path: Optional[str] = None):
        self.context_path = Path(context_path).resolve()
        self.dockerfile_path = (
            Path(dockerfile_path).resolve()
            if dockerfile_path
            else self.context_path / "Dockerfile"
        )

    def _check_docker_available(self) -> bool:
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
            )
            return result.returncode == 0
        except FileNotFoundError:
            return False

    def build(
        self,
        tag: Optional[str] = None,
        stream_output: bool = True,
        output_callback: Optional[Callable[[str], None]] = None,
    ) -> BuildResult:
        if not self._check_docker_available():
            return BuildResult(
                success=False,
                image_id=None,
                error="Docker is not available. Please install Docker and ensure it's running.",
            )

        if not self.dockerfile_path.exists():
            return BuildResult(
                success=False,
                image_id=None,
                error=f"Dockerfile not found at {self.dockerfile_path}",
            )

        cmd = [
            "docker",
            "build",
            "--platform",
            "linux/amd64",
            "-f",
            str(self.dockerfile_path),
        ]

        if tag:
            cmd.extend(["-t", tag])

        cmd.append(str(self.context_path))

        try:
            if stream_output:
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                )

                output_lines = []
                for line in iter(process.stdout.readline, ""):
                    output_lines.append(line)
                    if output_callback:
                        output_callback(line.rstrip())
                    else:
                        print(line, end="", flush=True)

                process.wait()
                full_output = "".join(output_lines)

                if process.returncode != 0:
                    return BuildResult(
                        success=False,
                        image_id=None,
                        error=f"Docker build failed with exit code {process.returncode}",
                    )

                image_id = self._extract_image_id(full_output, tag)
                return BuildResult(success=True, image_id=image_id, error=None)

            else:
                result = subprocess.run(cmd, capture_output=True, text=True)

                if result.returncode != 0:
                    return BuildResult(
                        success=False,
                        image_id=None,
                        error=result.stderr or result.stdout,
                    )

                image_id = self._extract_image_id(result.stdout, tag)
                return BuildResult(success=True, image_id=image_id, error=None)

        except Exception as e:
            return BuildResult(
                success=False,
                image_id=None,
                error=str(e),
            )

    def _extract_image_id(self, output: str, tag: Optional[str]) -> Optional[str]:
        if tag:
            try:
                result = subprocess.run(
                    ["docker", "images", "-q", tag],
                    capture_output=True,
                    text=True,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return result.stdout.strip().split("\n")[0]
            except Exception:
                pass

        for line in reversed(output.split("\n")):
            if "writing image sha256:" in line.lower():
                parts = line.split("sha256:")
                if len(parts) > 1:
                    return "sha256:" + parts[1].split()[0]

        return None
