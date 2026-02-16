import json
import os
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class MCPServerConfig(BaseModel):
    name: str
    type: Literal["stdio", "sse"]
    command: Optional[str] = None
    args: List[str] = Field(default_factory=list)
    url: Optional[str] = None


class AgentConfig(BaseSettings):
    gemini_api_key: Optional[str] = None
    mcp_servers: List[MCPServerConfig] = Field(default_factory=list)
    skills_path: str = "./skills"
    db_path: str = "agent.db"
    heartbeat_interval_minutes: float = 5.0
    shell_command_timeout: float = 30.0
    bus_max_tasks: int = 1000

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


def load_config(config_path: str = "agent.json") -> AgentConfig:
    data = {}
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            data = json.load(f)

    return AgentConfig(**data)
