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

## Test: React Chatbot

```bash
agent-deployer build sample_frontend -t chatbot:latest
docker run -d -p 3000:3000 --name chatbot chatbot:latest
open http://localhost:3000
docker stop chatbot && docker rm chatbot
```

## Library Usage

```python
from agent_deployer import ProjectAnalyzer, DockerfileAgent, DockerBuilder

analyzer = ProjectAnalyzer("/path/to/project")
context = analyzer.analyze()

agent = DockerfileAgent()
agent.generate_and_save(context)

builder = DockerBuilder("/path/to/project")
result = builder.build(tag="myapp:latest")
print(result.image_id)
```
