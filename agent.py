import json
import os
from typing import List, Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import McpToolset, StdioConnectionParams, SseConnectionParams
from google.adk.events import Event
from google.genai import types
import tools_internal
from config import AgentConfig
import functools

class AgentWrapper:
    def __init__(self, config: AgentConfig, skills_loader: Any):
        self.config = config
        self.skills_loader = skills_loader

        # Set API key for google-genai
        os.environ["GOOGLE_API_KEY"] = self.config.gemini_api_key

        self.agent = self._create_agent()

    def _create_agent(self) -> LlmAgent:
        # 1. Internal tools
        @functools.wraps(tools_internal.run_shell_command)
        async def run_shell_command(command: str) -> str:
            return await tools_internal.run_shell_command(command, timeout=self.config.shell_command_timeout)

        tools = [
            run_shell_command,
            tools_internal.list_files,
            tools_internal.read_file,
            tools_internal.write_file
        ]

        # 2. MCP Toolsets
        for mcp_cfg in self.config.mcp_servers:
            if mcp_cfg.type == "stdio":
                params = StdioConnectionParams(
                    command=mcp_cfg.command,
                    args=mcp_cfg.args
                )
            else:
                params = SseConnectionParams(
                    url=mcp_cfg.url
                )

            toolset = McpToolset(
                connection_params=params,
                tool_name_prefix=f"{mcp_cfg.name}_"
            )
            tools.append(toolset)

        # 3. Instructions from skills
        skills_prompt = self.skills_loader.load_skills()
        instruction = (
            "You are a helpful agent service running on a Linux machine.\n"
            f"{skills_prompt}\n"
            "If you need to ask the user a question or need more information, "
            "simply ask them in your response. End your response with [NEEDS_INPUT] "
            "if you are waiting for user feedback before continuing a task."
        )

        return LlmAgent(
            name="agent_service",
            model="gemini-1.5-flash",
            instruction=instruction,
            tools=tools
        )

    async def run_with_runner(self, runner: Any, user_id: str, session_id: str, content: str) -> Dict[str, Any]:
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=content)]
        )

        assistant_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            if event.author == self.agent.name and event.content:
                for part in event.content.parts:
                    if part.text:
                        assistant_text += part.text

        needs_input = "[NEEDS_INPUT]" in assistant_text

        return {
            "source_id": session_id,
            "user_id": user_id,
            "content": assistant_text,
            "needs_input": needs_input
        }
