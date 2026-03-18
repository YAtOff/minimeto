from __future__ import annotations

import logging

from meto.agent.autopilot.models import AutopilotSession, AutopilotTask

logger = logging.getLogger(__name__)


def assemble_context_capsule(session: AutopilotSession, current_task: AutopilotTask) -> str:
    """Assemble the initial context prompt for a sub-task.

    Includes the global goal, the current task, and the handover from the
    immediately preceding completed task.
    """
    if not session.roadmap:
        logger.warning("Assembling context capsule with empty roadmap")

    # Find previous task to get its handover
    previous_handover = ""
    try:
        task_index = session.roadmap.index(current_task)
    except ValueError:
        logger.error(f"Current task {current_task.id} not found in roadmap")
        task_index = -1

    if task_index > 0:
        prev_task = session.roadmap[task_index - 1]
        if prev_task.handover:
            previous_handover = (
                f"### ⬅️ Previous Task Handover ({prev_task.id})\n{prev_task.handover}\n"
            )

    capsule = (
        f"### 🎯 Global Goal\n{session.goal}\n\n"
        f"### 🛠️ Current Task\n{current_task.description}\n\n"
        f"{previous_handover}"
    )

    return capsule.strip()
