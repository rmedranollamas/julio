import json
import os
from typing import List, Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.genai import types
import tools_internal
from config import AgentConfig
import functools
from mcp_manager import MCPManager

class AgentWrapper:
    def __init__(self, config: AgentConfig, skills_loader: Any, mcp_manager: MCPManager):
        self.config = config
        self.skills_loader = skills_loader
        self.agent = None
        self.mcp_manager = mcp_manager

        # Set API key for google-genai
        os.environ["GOOGLE_API_KEY"] = self.config.gemini_api_key
        self.agent = None

    async def initialize(self):
        self.agent = await self._create_agent()

    @classmethod
    async def create(cls, config: AgentConfig, skills_loader: Any):
        instance = cls(config, skills_loader)
        instance.agent = await instance._create_agent()
        return instance

    async def _create_agent(self) -> LlmAgent:
        # 1. Internal tools
        @functools.wraps(tools_internal.run_shell_command)
        async def run_shell_command(command: str) -> str:
            return await tools_internal.run_shell_command(command, timeout=self.config.shell_command_timeout)

        tools = [
            run_shell_command,
            tools_internal.list_files,
            tools_internal.read_file,
            tools_internal.write_file,
            tools_internal.request_user_input
        ]

        # 2. MCP Toolsets from Manager
        tools.extend(self.mcp_manager.get_toolsets())

        # 3. Instructions from skills
        skills_prompt = await self.skills_loader.load_skills()
        instruction = (
            "You are a helpful agent service running on a Linux machine.\n"
            f"{skills_prompt}\n"
            "If you need more information from the user or need them to make a decision, "
            "use the `request_user_input` tool. "
            "Alternatively, if you are simply waiting for user feedback before continuing, "
            "end your response with [NEEDS_INPUT]."
        )

        return LlmAgent(
            name="agent_service",
            model="gemini-1.5-flash",
            instruction=instruction,
            tools=tools
        )

    async def process_command(self, runner: Any, source_id: str, user_id: str, content: str) -> Dict[str, Any]:
        # 1. Get history (Asynchronous Call)
        history = []
        if self.persistence:
            history = await self.persistence.get_history(source_id, user_id)

        # 2. Load skills context (Asynchronous Call)
        skills_context = await self.skills_loader.load_skills()

        # Log for internal use (e.g. debugging or future expansion)
        print(f"Loaded {len(history)} history events and {len(skills_context)} chars of skills context")

        return await self.run_with_runner(runner, user_id, source_id, content, history, skills_context)

    async def run_with_runner(self, runner: Any, user_id: str, session_id: str, content: str, history: List[Any] = None, skills_context: str = None) -> Dict[str, Any]:
        new_message = types.Content(
            role="user",
            parts=[types.Part(text=content)]
        )

        assistant_text = ""
        needs_input = False
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=new_message
        ):
            if event.author == self.agent.name and event.content:
                for part in event.content.parts:
                    if part.text:
                        assistant_text += part.text
                    if part.function_call and part.function_call.name == "request_user_input":
                        needs_input = True
                        if "question" in part.function_call.args:
                            q = part.function_call.args["question"]
                            if q not in assistant_text:
                                assistant_text += f"\n{q}"

        if "[NEEDS_INPUT]" in assistant_text:
            needs_input = True

        return {
            "source_id": session_id,
            "user_id": user_id,
            "content": assistant_text,
            "needs_input": needs_input
        }
