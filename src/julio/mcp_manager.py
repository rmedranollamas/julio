import asyncio
import logging
from typing import List, Tuple, Any, Dict
from mcp import StdioServerParameters
from google.adk.tools.mcp_tool.mcp_toolset import (
    McpToolset,
    StdioConnectionParams,
    SseConnectionParams,
)
from .config import MCPServerConfig

logger = logging.getLogger(__name__)


class MCPManager:
    """
    Manages dedicated tasks for MCP services to keep their contexts open.
    """

    def __init__(self, mcp_configs: List[MCPServerConfig]):
        self.configs = mcp_configs
        self.managed_servers: List[Tuple[McpToolset, str]] = []
        self._tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()
        self._cache: Dict[str, List[Any]] = {}
        self._in_progress_fetches: Dict[str, asyncio.Task] = {}
        self._cache_lock = asyncio.Lock()

        # Initialize toolsets
        for config in self.configs:
            try:
                if config.type == "stdio":
                    if not config.command:
                        logger.warning(
                            f"MCP server {config.name} is type 'stdio' but missing command. Skipping."
                        )
                        continue

                    # Note: Original code used (command=..., args=...) but library
                    # source shows it requires server_params: StdioServerParameters.
                    params = StdioConnectionParams(
                        server_params=StdioServerParameters(
                            command=config.command, args=config.args
                        )
                    )
                elif config.type == "sse":
                    if not config.url:
                        logger.warning(
                            f"MCP server {config.name} is type 'sse' but missing url. Skipping."
                        )
                        continue
                    params = SseConnectionParams(url=config.url)
                else:
                    logger.warning(
                        f"Unknown MCP server type '{config.type}' for {config.name}. Skipping."
                    )
                    continue

                toolset = McpToolset(
                    connection_params=params, tool_name_prefix=config.name
                )
                self.managed_servers.append((toolset, config.name))
            except Exception as e:
                logger.error(f"Failed to initialize toolset for {config.name}: {e}")

    async def start(self):
        """Starts dedicated tasks for each MCP service."""
        for toolset, name in self.managed_servers:
            task = asyncio.create_task(self._keep_alive(toolset, name))
            self._tasks.append(task)
        logger.info(f"Started {len(self._tasks)} MCP keep-alive tasks.")

    async def _keep_alive(self, toolset: McpToolset, name: str):
        """Dedicated task to keep the MCP session open."""
        logger.info(f"Starting dedicated keep-alive task for MCP server: {name}")
        while not self._stop_event.is_set():
            try:
                # Use public get_tools() to ensure connection is established and alive.
                # This avoids relying on private attributes of McpToolset.
                await self._fetch_and_cache(toolset, name)

                # Wait for next check or stop event
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=30)
                    break  # Stop event set
                except asyncio.TimeoutError:
                    pass  # Continue loop
            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._stop_event.is_set():
                    break
                logger.error(
                    f"Error in MCP keep-alive for {name}: {e}. Retrying in 5s..."
                )
                try:
                    await asyncio.wait_for(self._stop_event.wait(), timeout=5)
                except asyncio.TimeoutError:
                    pass
                except asyncio.CancelledError:
                    break

    def get_toolsets(self) -> List[McpToolset]:
        """Returns the list of managed toolsets."""
        return [toolset for toolset, _ in self.managed_servers]

    def _process_tools(self, tools: List[Any], name: str) -> List[Any]:
        """Processes raw tools into tool declarations."""
        processed = []
        for tool in tools:
            # Handle McpTool objects vs raw declarations
            if hasattr(tool, "_get_declaration"):
                try:
                    decl = tool._get_declaration()
                    if hasattr(decl, "model_dump"):
                        processed.append(decl.model_dump())
                    else:
                        processed.append(decl)
                except Exception as e:
                    logger.error(f"Error extracting declaration for tool from {name}: {e}")
            else:
                processed.append(tool)
        return processed

    async def _fetch_and_cache(self, toolset: McpToolset, name: str):
        """Fetches tools from a server, processes them, and updates the cache."""
        try:
            tools = await toolset.get_tools_with_prefix()
            processed = self._process_tools(tools, name)
            async with self._cache_lock:
                self._cache[name] = processed
        except Exception as e:
            logger.error(f"Failed to fetch tools for {name}: {e}")
        finally:
            async with self._cache_lock:
                self._in_progress_fetches.pop(name, None)

    async def get_tools(self) -> List[Any]:
        """
        Calls get_tools() on all managed McpToolset instances in parallel
        and returns an aggregated list of tool declarations.
        """
        if not self.managed_servers:
            return []

        # Phase 1 & 2: Identify missing and start/track fetches to avoid stampede
        tasks_to_wait = []
        async with self._cache_lock:
            for toolset, name in self.managed_servers:
                if name not in self._cache:
                    if name not in self._in_progress_fetches:
                        self._in_progress_fetches[name] = asyncio.create_task(
                            self._fetch_and_cache(toolset, name)
                        )
                    tasks_to_wait.append(self._in_progress_fetches[name])

        if tasks_to_wait:
            await asyncio.gather(*tasks_to_wait, return_exceptions=True)

        # Phase 3: Assemble the final list from the cache, preserving order.
        final_tools = []
        async with self._cache_lock:
            for _, name in self.managed_servers:
                final_tools.extend(self._cache.get(name, []))
        return final_tools

    async def list_tools(self) -> List[Any]:
        """Alias for get_tools() to satisfy unit tests."""
        return await self.get_tools()

    async def stop(self):
        """Stops all dedicated tasks and closes toolsets."""
        self._stop_event.set()
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        for toolset, _ in self.managed_servers:
            await toolset.close()
        logger.info("Stopped all MCP keep-alive tasks and closed sessions.")

    async def close(self):
        """Stops all dedicated tasks and closes toolsets (alias for stop)."""
        await self.stop()
