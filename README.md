# Persistent Agent Service (Julio)

A lightweight, persistent agent service designed to run on Linux (Docker-compatible) that interacts via an in-memory message bus and supports Model Context Protocol (MCP) and Agent Skills.

## Features

- **Gemini Integration**: Uses Google's Gemini LLM for reasoning and tool use.
- **Message Bus Architecture**: Asynchronous communication via an in-memory `asyncio.Queue` based bus (`agent_commands` and `agent_responses` channels).
- **Tool Support**:
  - **Internal Tools**: Full shell command execution and filesystem access.
  - **MCP Integration**: Support for both stdio and SSE MCP servers.
- **Agent Skills**: Implements the `agentskills.io` specification for loading procedural knowledge.
- **Persistence**: SQLite-backed history and state management with optimized shared connections and JSON parsing offloading.
- **Heartbeat**: Periodic self-triggering mechanism for background tasks.

## Architecture

The agent is built with a clean `src` layout and minimal dependencies:

- `src/julio/main.py`: Service orchestration and lifecycle management.
- `src/julio/agent.py`: LLM logic and tool orchestration.
- `src/julio/bus.py`: In-memory message bus with worker pool.
- `src/julio/mcp_manager.py`: MCP client implementation with keep-alive tasks.
- `src/julio/skills_loader.py`: Skill discovery and loading with file watching.
- `src/julio/persistence.py`: State and history management using SQLite.

## Getting Started

1. **Configure**: Edit `agent.json` with your `gemini_api_key`.
1. **Install Dependencies**:
   ```bash
   uv sync
   ```
1. **Run Locally**:
   ```bash
   uv run julio-agent
   ```
1. **Build & Run with Docker**:
   ```bash
   docker build -t julio-agent .
   docker run julio-agent
   ```
1. **Interact**:
   The service listens for commands on the `agent_commands` channel of the internal bus. For external interaction, you can use the provided scripts or integrate a bridge.

## Development & Testing

Run tests:

```bash
uv run pytest tests/
```

Run performance benchmarks:

```bash
uv run python scripts/performance/standalone_json_perf.py
```

Run the demo simulation:

```bash
uv run python scripts/demo_service.py
```
