import json
import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class MCPServerConfig(BaseModel):
    name: str
    type: Literal["stdio", "sse"]
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class AgentConfig(BaseModel):
    gemini_api_key: str
    mcp_servers: List[MCPServerConfig] = Field(default_factory=list)
    skills_path: str = "/skills"
    db_path: str = "agent.db"
    heartbeat_interval_minutes: float = 5.0
    shell_command_timeout: float = 30.0


def load_config(config_path: str = "agent.json") -> AgentConfig:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found: {config_path}")

    with open(config_path, "r") as f:
        data = json.load(f)

    return AgentConfig(**data)
