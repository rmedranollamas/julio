import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from typing import List, Dict, Any, Optional
from config import MCPServerConfig

class MCPManager:
    def __init__(self, configs: List[MCPServerConfig]):
        self.configs = configs
        self.sessions: Dict[str, ClientSession] = {}
        self._exit_stack = None

    async def connect_all(self):
        for config in self.configs:
            try:
                if config.type == "stdio":
                    # Stdio connection needs to be managed carefully with contexts
                    # For now, we'll store the session, but we might need a better way to keep it alive
                    params = StdioServerParameters(
                        command=config.command,
                        args=config.args,
                        env=None
                    )
                    # This is tricky because stdio_client is an async context manager
                    # We'll need to keep the context open.
                    # For a permanent service, we might need a dedicated task for each.
                    pass
                elif config.type == "sse":
                    # Similar for SSE
                    pass
            except Exception as e:
                print(f"Failed to connect to MCP server {config.name}: {e}")

    # I'll implement a simpler version that connects on demand or maintains a pool.
    # Actually, the MCP SDK is designed around context managers.
    # To keep them alive, I'll use an AsyncExitStack.

    async def start(self):
        from contextlib import AsyncExitStack
        self._exit_stack = AsyncExitStack()
        for config in self.configs:
            try:
                if config.type == "stdio":
                    params = StdioServerParameters(command=config.command, args=config.args)
                    read, write = await self._exit_stack.enter_async_context(stdio_client(params))
                    session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    self.sessions[config.name] = session
                    print(f"Connected to stdio MCP: {config.name}")
                elif config.type == "sse":
                    read, write = await self._exit_stack.enter_async_context(sse_client(config.url))
                    session = await self._exit_stack.enter_async_context(ClientSession(read, write))
                    await session.initialize()
                    self.sessions[config.name] = session
                    print(f"Connected to sse MCP: {config.name}")
            except Exception as e:
                print(f"Failed to connect to {config.name}: {e}")

    async def stop(self):
        if self._exit_stack:
            await self._exit_stack.aclose()

    async def list_tools(self) -> List[Dict[str, Any]]:
        all_tools = []
        for name, session in self.sessions.items():
            tools = await session.list_tools()
            for tool in tools.tools:
                # Prefix tool name with server name to avoid collisions
                tool_dict = {
                    "server": name,
                    "name": tool.name,
                    "description": tool.description,
                    "input_schema": tool.inputSchema
                }
                all_tools.append(tool_dict)
        return all_tools

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Any:
        if server_name in self.sessions:
            result = await self.sessions[server_name].call_tool(tool_name, arguments)
            return result
        raise ValueError(f"Server {server_name} not found")
