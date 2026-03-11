"""Custom exception types used across the agent runtime."""


class AgentError(Exception):
    """Base class for meto agent errors."""


class ContextForkError(AgentError):
    """Raised when a context cannot be forked (e.g., logging directory creation fails)."""


class SessionNotFoundError(AgentError):
    """Raised when a session file cannot be found."""


class SubagentError(AgentError):
    """Raised when a subagent cannot be created or executed."""


class MaxStepsExceededError(AgentError):
    """Raised when the agent loop exceeds its configured turn budget."""


class ToolExecutionError(AgentError):
    """Raised when a tool fails to execute (tool runner layer)."""


class ToolNotFoundError(AgentError):
    """Raised when an unknown tool name is requested."""


class AgentInterrupted(AgentError):
    """Raised when the agent loop is interrupted by user (Ctrl-C)."""


class SkillAgentNotFoundError(AgentError):
    """Raised when a skill-local agent is not found."""


class SkillAgentValidationError(AgentError):
    """Raised when a skill-local agent fails validation."""


class MCPInitializationError(AgentError):
    """Raised when MCP tools cannot be initialized or discovered."""


class LLMError(AgentError):
    """Raised when an error occurs while calling the LLM API (OpenAI/LiteLLM)."""
