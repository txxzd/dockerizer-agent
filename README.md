# Agent Deployer

AI-powered Dockerfile generation and Docker image building using Gemini.

## Setup

```bash
pip install -e .
```

Create `.env` file:
```
GEMINI_API_KEY=your-api-key
```

## CLI Commands

```bash
agent-deployer analyze <path>                    # Analyze project
agent-deployer generate <path>                   # Generate Dockerfile
agent-deployer build <path> -t <tag>             # Build image
agent-deployer build <path> -t <tag> -q          # Quiet mode (output URI only)
agent-deployer build <path> -t <tag> --regenerate  # Force regenerate Dockerfile
```

## Library Usage

```python
from agent_deployer import DockerfileAgent, DockerBuilder

agent = DockerfileAgent()
agent.run("/path/to/project")

builder = DockerBuilder("/path/to/project")
result = builder.build(tag="myapp:latest")
print(result.image_id)
```
