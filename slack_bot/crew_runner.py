from __future__ import annotations

from pathlib import Path
from typing import Any

from crewai.project.crew_loader import load_crew


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CREW_PATH = PROJECT_ROOT / "crew.jsonc"


def run_content_crew(
    *,
    subject: str,
    post_count: int,
    content_style: str,
    memory_context: str = "",
) -> str:
    """
    Load the JSON-first CrewAI project and run it with Slack inputs
    and approved-content memory.
    """

    if not CREW_PATH.exists():
        raise FileNotFoundError(
            f"Crew configuration not found: {CREW_PATH}"
        )

    crew, default_inputs = load_crew(CREW_PATH)

    inputs: dict[str, Any] = {
        **default_inputs,
        "subject": subject,
        "post_count": post_count,
        "content_style": content_style,
        "recent_content_memory": (
            memory_context.strip()
            or (
                "No approved previous content exists. "
                "Create original content."
            )
        ),
    }

    result = crew.kickoff(inputs=inputs)

    raw_result = getattr(result, "raw", None)

    if raw_result:
        return str(raw_result).strip()

    return str(result).strip()