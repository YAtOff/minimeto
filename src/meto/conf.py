"""Configuration management for meto using Pydantic Settings."""

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings configurable via environment variables and .env file.

    Environment variables must be prefixed with METO_.
    Example: METO_LLM_API_KEY=your_api_key
    """

    model_config = SettingsConfigDict(  # pyright: ignore[reportUnannotatedClassAttribute]
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="METO_",
        case_sensitive=False,
        extra="ignore",
    )

    LLM_API_KEY: str = Field(
        default="",
        description="API key for LiteLLM proxy",
    )

    LLM_BASE_URL: str = Field(
        default="http://localhost:4444",
        description="Base URL for LiteLLM proxy",
    )

    DEFAULT_MODEL: str = Field(
        default="gpt-4.1",
        description="Default model name to use with LiteLLM",
    )

    MODEL_CONTEXT_WINDOWS: dict[str, int] = Field(
        default={
            "gpt-4.1": 128000,
            "gpt-4o": 128000,
            "gpt-4o-mini": 128000,
            "claude-sonnet-4": 200000,
            "glm-4.7": 200000,
        },
        description="Context window sizes per model.",
    )

    # --- Agent loop tuning ---

    MAIN_AGENT_MAX_TURNS: int = Field(
        default=100,
        description="Maximum iterations for main agent per prompt.",
    )

    SUBAGENT_MAX_TURNS: int = Field(
        default=25,
        description="Maximum iterations for subagents per task.",
    )

    TOOL_TIMEOUT_SECONDS: int = Field(
        default=300,
        description="Timeout (seconds) for shell tool execution.",
    )

    MAX_TOOL_OUTPUT_CHARS: int = Field(
        default=50000,
        description="Maximum characters captured from tool result.",
    )

    # --- Directories ---

    SESSION_DIR: Path = Field(
        default=Path.home() / ".minimeto" / "sessions",
        description="Directory to store session files.",
    )

    @field_validator("SESSION_DIR")
    @classmethod
    def ensure_dir_exists(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    AGENTS_DIR: Path = Field(
        default=Path.cwd() / ".meto" / "agents",
        description="Directory for user-defined agent files.",
    )

    SKILLS_DIR: Path = Field(
        default=Path.cwd() / ".meto" / "skills",
        description="Directory for skill directories.",
    )

    # --- Agent Features ---

    AGENT_FEATURES: list[str] = Field(
        default=["agentsmd", "todo_manager"],
        description="Enabled agent features: agentsmd, subagents, skills, todo_manager",
    )

    # --- Logging ---

    LOG_DIR: Path = Field(
        default=Path.home() / ".minimeto" / "logs",
        description="Directory for agent reasoning trace logs.",
    )

    @field_validator("LOG_DIR")
    @classmethod
    def ensure_log_dir(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v


# Global settings instance
settings = Settings()
