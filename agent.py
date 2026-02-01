import google.generativeai as genai
from typing import List, Dict, Any, Optional
import json
import asyncio
from config import AgentConfig
from persistence import Persistence
from mcp_manager import MCPManager
from skills_loader import SkillsLoader
import tools_internal

class Agent:
    def __init__(self, config: AgentConfig, persistence: Persistence, mcp_manager: MCPManager, skills_loader: SkillsLoader):
        self.config = config
        self.persistence = persistence
        self.mcp_manager = mcp_manager
        self.skills_loader = skills_loader
        self._model_cache = {}

        genai.configure(api_key=self.config.gemini_api_key)

    async def _call_mcp_tool(self, server_name: str, tool_name: str, arguments_json: str) -> str:
        """Calls a tool on a specific MCP server. arguments_json should be a JSON string of arguments."""
        try:
            args = json.loads(arguments_json)
            result = await self.mcp_manager.call_tool(server_name, tool_name, args)
            return str(result)
        except Exception as e:
            return f"Error calling MCP tool: {e}"

    def _get_all_tools(self):
        return [
            tools_internal.run_shell_command,
            tools_internal.list_files,
            tools_internal.read_file,
            tools_internal.write_file,
            self._call_mcp_tool
        ]

    async def _get_model(self, system_instruction: str):
        if system_instruction not in self._model_cache:
            self._model_cache[system_instruction] = genai.GenerativeModel(
                model_name='gemini-1.5-flash',
                tools=self._get_all_tools(),
                system_instruction=system_instruction
            )
        return self._model_cache[system_instruction]

    async def process_command(self, source_id: str, user_id: str, content: str) -> Dict[str, Any]:
        # 1. Get history
        history = self.persistence.get_history(source_id, user_id)

        # 2. Load skills context
        skills_prompt = self.skills_loader.load_skills()

        # 3. List available MCP tools for the system prompt
        mcp_tools = await self.mcp_manager.list_tools()
        mcp_prompt = "\nAvailable MCP Tools:\n" + json.dumps(mcp_tools, indent=2)

        system_instruction = (
            "You are a helpful agent service running on a Linux machine.\n"
            f"{skills_prompt}\n"
            f"{mcp_prompt}\n"
            "Use the '_call_mcp_tool' function to interact with MCP servers.\n"
            "If you need to ask the user a question or need more information, "
            "simply ask them in your response. End your response with [NEEDS_INPUT] "
            "if you are waiting for user feedback before continuing a task."
        )

        # 4. Get or create model
        model = await self._get_model(system_instruction)

        gemini_history = []
        for h in history:
            role = 'user' if h['role'] == 'user' else 'model'
            gemini_history.append({'role': role, 'parts': [h['content']]})

        # Use automatic function calling
        chat = model.start_chat(history=gemini_history, enable_automatic_function_calling=True)

        # 4. Record user message
        self.persistence.add_history(source_id, user_id, "user", content)

        # 5. Process with Gemini
        try:
            response = await chat.send_message_async(content)
            assistant_text = response.text
        except Exception as e:
            assistant_text = f"Error: {e}"

        # 6. Record assistant response
        self.persistence.add_history(source_id, user_id, "assistant", assistant_text)

        # 7. Detect if user input is needed
        needs_input = "[NEEDS_INPUT]" in assistant_text

        return {
            "source_id": source_id,
            "user_id": user_id,
            "content": assistant_text,
            "needs_input": needs_input
        }
