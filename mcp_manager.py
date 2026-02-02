import asyncio
import logging
from typing import List, Dict, Optional
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, SseConnectionParams
from mcp import StdioServerParameters
from config import MCPServerConfig

logger = logging.getLogger(__name__)

class MCPManager:
    """
    Manages MCP (Model Context Protocol) toolsets and their sessions.
    Provides proactive health checks and reconnection logic for robust stdio connections.
    """
    def __init__(self, configs: List[MCPServerConfig]):
        self.configs = configs
        self.toolsets: Dict[str, McpToolset] = {}
        self._health_check_task: Optional[asyncio.Task] = None
        self._initialize_toolsets()

    def _initialize_toolsets(self):
        """Initializes toolsets based on the provided configurations."""
        for cfg in self.configs:
            try:
                if cfg.type == "stdio":
                    # Stdio connection needs to be managed carefully with contexts
                    # Reusing ADK primitives: StdioConnectionParams wraps StdioServerParameters
                    params = StdioConnectionParams(
                        server_params=StdioServerParameters(
                            command=cfg.command,
                            args=cfg.args
                        )
                    )
                elif cfg.type == "sse":
                    params = SseConnectionParams(
                        url=cfg.url
                    )
                else:
                    logger.error(f"Unsupported MCP server type: {cfg.type} for server {cfg.name}")
                    continue

                toolset = McpToolset(
                    connection_params=params,
                    tool_name_prefix=f"{cfg.name}_"
                )
                self.toolsets[cfg.name] = toolset
            except Exception as e:
                logger.error(f"Failed to initialize toolset for MCP server {cfg.name}: {e}")

    async def start(self):
        """Starts the MCP Manager, attempting initial connections and starting the health check loop."""
        logger.info("Starting MCP Manager...")

        # Proactively attempt to initialize connections to each MCP server
        for name, toolset in self.toolsets.items():
            try:
                # Calling get_tools() triggers the MCP session creation and initialization
                await toolset.get_tools()
                logger.info(f"Successfully initialized MCP server: {name}")
            except Exception as e:
                # We don't want to block startup if an MCP server is down,
                # health check and reactive reconnection will handle it later.
                logger.warning(f"Initial connection to MCP server {name} failed: {e}. Will retry in background.")

        # Start the proactive health check loop to keep connections alive
        self._health_check_task = asyncio.create_task(self._health_check_loop())

    async def _health_check_loop(self):
        """Periodically verifies that connections are alive and triggers reconnection if needed."""
        while True:
            try:
                await asyncio.sleep(60) # Health check interval: 1 minute
                for name, toolset in self.toolsets.items():
                    try:
                        # get_tools() will check if the session is still active
                        # and reconnect if it has been closed or crashed.
                        await toolset.get_tools()
                        logger.debug(f"MCP server {name} health check passed.")
                    except Exception as e:
                        logger.error(f"MCP server {name} health check failed: {e}")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in MCP health check loop: {e}")

    async def stop(self):
        """Stops the health check loop and closes all MCP toolsets."""
        logger.info("Stopping MCP Manager...")
        if self._health_check_task:
            self._health_check_task.cancel()
            try:
                await self._health_check_task
            except asyncio.CancelledError:
                pass

        # Properly close each toolset to release resources (like child processes)
        for name, toolset in self.toolsets.items():
            try:
                await toolset.close()
                logger.info(f"Closed MCP toolset: {name}")
            except Exception as e:
                logger.error(f"Error closing MCP toolset {name}: {e}")

    def get_toolsets(self) -> List[McpToolset]:
        """Returns all managed McpToolset instances."""
        return list(self.toolsets.values())
