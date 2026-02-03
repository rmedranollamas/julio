import json
import os
from typing import List, Dict, Any, Optional
from google.adk.agents import LlmAgent
from google.adk.events import Event
from google.genai import types
import tools_internal
from config import AgentConfig
from mcp_manager import MCPManager

class AgentWrapper:
    def __init__(self, config: AgentConfig, skills_loader: Any, mcp_manager: MCPManager):
        self.config = config
        self.skills_loader = skills_loader
        self.mcp_manager = mcp_manager

        # Set API key for google-genai
        os.environ["GOOGLE_API_KEY"] = self.config.gemini_api_key

        self.agent = self._create_agent()

    def _create_agent(self) -> LlmAgent:
        # 1. Internal tools
        tools = [
            tools_internal.run_shell_command,
            tools_internal.list_files,
            tools_internal.read_file,
            tools_internal.write_file,
            tools_internal.request_user_input
        ]

        # 2. MCP Toolsets from Manager
        tools.extend(self.mcp_manager.get_toolsets())

        # 3. Instructions from skills
        skills_prompt = self.skills_loader.load_skills()
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

    async def run_with_runner(self, runner: Any, user_id: str, session_id: str, content: str) -> Dict[str, Any]:
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
