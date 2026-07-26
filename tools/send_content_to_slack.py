import os
from typing import Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class SlackMessageInput(BaseModel):
    """Input schema for sending content to Slack."""

    message: str = Field(
        ...,
        description="The complete publication-ready LinkedIn content to send to Slack.",
    )


class SendContentToSlackTool(BaseTool):
    name: str = "Send Content to Slack"
    description: str = (
        "Send the complete final LinkedIn content package to the configured "
        "Slack channel. Use this tool only after the content has been finalized."
    )
    args_schema: Type[BaseModel] = SlackMessageInput

    def _run(self, message: str) -> str:
        webhook_url = os.getenv("SLACK_WEBHOOK_URL")

        if not webhook_url:
            return "Slack message failed: SLACK_WEBHOOK_URL is missing from .env."

        if not message.strip():
            return "Slack message failed: message content is empty."

        try:
            response = requests.post(
                webhook_url,
                json={"text": message},
                timeout=20,
            )
            response.raise_for_status()
            return "Final LinkedIn content was sent to Slack successfully."

        except requests.RequestException as exc:
            return f"Slack message failed: {exc}"