import os
import functools
from typing import Dict, Any
from google.adk.agents import LlmAgent
from google.genai import types
from . import tools_internal
from .config import AgentConfig
from .mcp_manager import MCPManager


class AgentWrapper:
    """
    Wrapper for ADK LlmAgent to handle initialization and command processing.
    """

    def __init__(
        self,
        config: AgentConfig,
        skills_loader: Any,
        mcp_manager: MCPManager,
        persistence: Any,
    ):
        self.config = config
        self.skills_loader = skills_loader
        self.mcp_manager = mcp_manager
        self.persistence = persistence
        self.agent: LlmAgent | None = None

        # Set API key for google-genai
        if self.config.gemini_api_key:
            os.environ["GOOGLE_API_KEY"] = self.config.gemini_api_key
        else:
            # Set a placeholder to prevent initialization errors if not provided yet.
            # Actual calls will fail later with a proper error if still missing.
            os.environ.setdefault("GOOGLE_API_KEY", "MISSING_API_KEY")

    async def initialize(self):
        """Initializes the underlying ADK agent."""
        if not self.agent:
            self.agent = await self._create_agent()

    @classmethod
    async def create(
        cls,
        config: AgentConfig,
        skills_loader: Any,
        mcp_manager: MCPManager,
        persistence: Any,
    ):
        """Factory method to create and initialize an AgentWrapper."""
        instance = cls(config, skills_loader, mcp_manager, persistence)
        await instance.initialize()
        return instance

    async def _create_agent(self) -> LlmAgent:
        # 1. Internal tools with configuration applied
        @functools.wraps(tools_internal.run_shell_command)
        async def run_shell_command(command: str) -> str:
            return await tools_internal.run_shell_command(
                command, timeout=self.config.shell_command_timeout
            )

        tools = [
            run_shell_command,
            tools_internal.list_files,
            tools_internal.read_file,
            tools_internal.write_file,
            tools_internal.request_user_input,
        ]

        # 2. Add MCP Toolsets from the manager
        tools.extend(self.mcp_manager.get_toolsets())

        # 3. Load dynamic skills instructions
        skills_prompt = await self.skills_loader.load_skills()
        instruction = (
            "You are a helpful agent service running on a Linux machine.\n"
            f"{skills_prompt}\n\n"
            "Guidelines:\n"
            "- Use 'request_user_input' if you need the user to make a decision or provide more info.\n"
            "- If you are waiting for feedback without a tool call, end your response with [NEEDS_INPUT].\n"
            "- Be concise and professional."
        )

        return LlmAgent(
            name="agent_service",
            model="gemini-1.5-flash",
            instruction=instruction,
            tools=tools,
        )

    async def process_command(
        self, runner: Any, source_id: str, user_id: str, content: str
    ) -> Dict[str, Any]:
        """Processes a user command through the ADK runner and handles output aggregation."""
        new_message = types.Content(role="user", parts=[types.Part(text=content)])

        assistant_text_parts = []
        needs_input = False
        seen_questions = set()

        async for event in runner.run_async(
            user_id=user_id, session_id=source_id, new_message=new_message
        ):
            if event.author == self.agent.name and event.content:
                for part in event.content.parts:
                    if part.text:
                        assistant_text_parts.append(part.text)

                    if (
                        part.function_call
                        and part.function_call.name == "request_user_input"
                    ):
                        needs_input = True
                        if "question" in part.function_call.args:
                            q = part.function_call.args["question"]
                            if q not in seen_questions:
                                assistant_text_parts.append(f"\n{q}")
                                seen_questions.add(q)

        assistant_text = "".join(assistant_text_parts).strip()

        if "[NEEDS_INPUT]" in assistant_text:
            needs_input = True

        return {
            "source_id": source_id,
            "user_id": user_id,
            "content": assistant_text,
            "needs_input": needs_input,
        }
