# Persistent Agent Service

A lightweight, persistent agent service designed to run on Linux (Docker-compatible) that interacts via a Redis message bus and supports Model Context Protocol (MCP) and Agent Skills.

## Features

- **Gemini Integration**: Uses Google's Gemini LLM for reasoning and tool use.
- **Message Bus Architecture**: Asynchronous communication via Redis (`agent_commands` and `agent_responses` channels).
- **Tool Support**:
  - **Internal Tools**: Full shell command execution and filesystem access.
  - **MCP Integration**: Support for both stdio and SSE MCP servers.
- **Agent Skills**: Implements the `agentskills.io` specification for loading procedural knowledge.
- **Persistence**: SQLite-backed history and state management.
- **Heartbeat**: Periodic self-triggering mechanism for background tasks.

## Architecture

The agent is built without heavy frameworks to maintain performance and simplicity:
- `main.py`: Service orchestration and lifecycle management.
- `agent.py`: LLM logic and tool orchestration.
- `bus.py`: Async Redis communication.
- `mcp_manager.py`: MCP client implementation.
- `skills_loader.py`: Skill discovery and loading.
- `persistence.py`: State and history management.

## Getting Started

1.  **Configure**: Edit `agent.json` with your `gemini_api_key` and Redis URL.
2.  **Install Dependencies**:
    ```bash
    uv sync
    ```
3.  **Run Locally**:
    ```bash
    uv run python main.py
    ```
4.  **Build & Run with Docker**:
    ```bash
    docker build -t agent-service .
    docker run agent-service
    ```
5.  **Interact**:
    Publish a JSON message to `agent_commands`:
    ```json
    {
      "source_id": "chat-interface",
      "user_id": "user-123",
      "content": "List the files in the current directory"
    }
    ```

## Development & Testing

Run tests with coverage:
```bash
uv run pytest
uv run coverage run -m pytest
uv run coverage report -m
```

Run the demo simulation:
```bash
uv run python demo_service.py
```
