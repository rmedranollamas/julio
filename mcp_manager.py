import asyncio
import logging
from typing import List, Optional, Dict, Any, Union, TextIO
import sys

from mcp import StdioServerParameters
from google.adk.tools.base_toolset import BaseToolset, ToolPredicate
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, SseConnectionParams
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool

logger = logging.getLogger(__name__)

class MCPManager(BaseToolset):
    """Manages multiple MCP toolsets and parallelizes tool discovery."""

    def __init__(
        self,
        server_configs: List[Any],
        tool_filter: Optional[Union[ToolPredicate, List[str]]] = None,
        errlog: TextIO = sys.stderr,
    ):
        super().__init__(tool_filter=tool_filter)
        self.toolsets: Dict[str, McpToolset] = {}

        for mcp_cfg in server_configs:
            params = None
            if mcp_cfg.type == "stdio":
                # To be robust across different ADK versions, we try to support both formats.
                # The newer format expects server_params as a StdioServerParameters object.
                try:
                    params = StdioConnectionParams(
                        server_params=StdioServerParameters(
                            command=mcp_cfg.command,
                            args=mcp_cfg.args
                        )
                    )
                except Exception:
                    # Fallback to older format or direct assignment if the above fails
                    try:
                        params = StdioConnectionParams(
                            command=mcp_cfg.command,
                            args=mcp_cfg.args
                        )
                    except Exception as e:
                        logger.error(f"Failed to initialize StdioConnectionParams for {mcp_cfg.name}: {e}")
                        continue
            else:
                params = SseConnectionParams(
                    url=mcp_cfg.url
                )

            if params:
                toolset = McpToolset(
                    connection_params=params,
                    tool_name_prefix=f"{mcp_cfg.name}_",
                    errlog=errlog
                )
                self.toolsets[mcp_cfg.name] = toolset

    async def get_tools(
        self,
        readonly_context: Optional[ReadonlyContext] = None,
    ) -> List[BaseTool]:
        """Return all tools from all managed MCP servers in parallel."""
        if not self.toolsets:
            return []

        tasks = [ts.get_tools(readonly_context) for ts in self.toolsets.values()]
        results = await asyncio.gather(*tasks)

        all_tools = []
        for tools in results:
            all_tools.extend(tools)
        return all_tools

    async def list_tools(self) -> List[Dict[str, Any]]:
        """
        Parallelizes tool discovery and returns tool definitions as dictionaries.
        This matches the signature and intent of the original requested optimization.
        """
        if not self.toolsets:
            return []

        async def get_tool_dicts_from_ts(ts):
            tools = await ts.get_tools()
            tool_dicts = []
            for tool in tools:
                # Use the public/documented way to get tool declarations if possible
                # or fallback to model_dump if it's a pydantic-like object.
                try:
                    decl = tool._get_declaration()
                    if hasattr(decl, "model_dump"):
                        d = decl.model_dump()
                    else:
                        d = dict(decl)
                    tool_dicts.append(d)
                except Exception as e:
                    logger.warning(f"Could not get declaration for tool {tool.name}: {e}")
            return tool_dicts

        tasks = [get_tool_dicts_from_ts(ts) for ts in self.toolsets.values()]
        results = await asyncio.gather(*tasks)

        all_tools = []
        for result in results:
            all_tools.extend(result)
        return all_tools

    async def close(self) -> None:
        """Close all managed toolsets in parallel."""
        if not self.toolsets:
            return

        tasks = [ts.close() for ts in self.toolsets.values()]
        await asyncio.gather(*tasks, return_exceptions=True)
