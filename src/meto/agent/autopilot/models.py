from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class AutopilotTaskStatus(StrEnum):
    """Status of an autopilot task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AutopilotTask(BaseModel):
    """A single task within an autopilot roadmap."""

    id: str = Field(description="Unique identifier for the task (e.g., '1.1')")
    description: str = Field(description="Human-readable description of the task")
    status: AutopilotTaskStatus = Field(default=AutopilotTaskStatus.PENDING)
    handover: str | None = Field(
        default=None, description="Handover documentation from task completion"
    )
    error: str | None = Field(default=None, description="Error message if the task failed")
    attempts: int = Field(default=0, description="Number of execution attempts")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional task metadata")


class AutopilotSession(BaseModel):
    """State for an entire autopilot session."""

    goal: str = Field(description="The global goal being pursued")
    roadmap: list[AutopilotTask] = Field(default_factory=list, description="The sequence of tasks")
    current_task_id: str | None = Field(
        default=None, description="The ID of the task currently running"
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional session metadata"
    )

    def get_task(self, task_id: str) -> AutopilotTask | None:
        """Find a task by its ID."""
        for task in self.roadmap:
            if task.id == task_id:
                return task
        return None

    def get_next_pending_task(self) -> AutopilotTask | None:
        """Find the first task that is pending or failed."""
        for task in self.roadmap:
            if task.status in (AutopilotTaskStatus.PENDING, AutopilotTaskStatus.FAILED):
                return task
        return None

    @property
    def progress(self) -> tuple[int, int]:
        """Return (completed, total) task counts."""
        completed = sum(1 for t in self.roadmap if t.status == AutopilotTaskStatus.COMPLETED)
        return completed, len(self.roadmap)
