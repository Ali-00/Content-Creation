from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from slack_bot.conversation_state import (
    Conversation,
    conversation_store,
)
from slack_bot.crew_runner import run_content_crew


load_dotenv()

SLACK_BOT_TOKEN = os.getenv("SLACK_BOT_TOKEN")
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")

if not SLACK_BOT_TOKEN:
    raise RuntimeError("SLACK_BOT_TOKEN is missing from .env")

if not SLACK_APP_TOKEN:
    raise RuntimeError("SLACK_APP_TOKEN is missing from .env")

if not SLACK_SIGNING_SECRET:
    raise RuntimeError("SLACK_SIGNING_SECRET is missing from .env")


app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)

# The LLM workflow is blocking and may take several minutes.
# Running it in a worker keeps the Slack event listener responsive.
executor = ThreadPoolExecutor(max_workers=2)


VALID_POST_COUNTS = {1, 3, 5}

STYLE_ALIASES = {
    "educational": "Educational",
    "education": "Educational",
    "opinion": "Opinion",
    "practitioner": "Practitioner Insight",
    "practitioner insight": "Practitioner Insight",
    "mixed": "Mixed",
}


def remove_bot_mention(text: str) -> str:
    """Remove Slack's <@BOT_ID> markup from a message."""

    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def split_slack_message(
    text: str,
    max_length: int = 3500,
) -> list[str]:
    """
    Split long output into Slack-safe chunks while trying to preserve paragraphs.
    """

    text = text.strip()

    if len(text) <= max_length:
        return [text]

    chunks: list[str] = []
    current = ""

    for paragraph in text.split("\n\n"):
        candidate = f"{current}\n\n{paragraph}".strip()

        if len(candidate) <= max_length:
            current = candidate
            continue

        if current:
            chunks.append(current)

        # Handle a single paragraph longer than max_length.
        while len(paragraph) > max_length:
            chunks.append(paragraph[:max_length])
            paragraph = paragraph[max_length:]

        current = paragraph

    if current:
        chunks.append(current)

    return chunks


def post_thread_message(
    client,
    channel_id: str,
    thread_ts: str,
    text: str,
) -> None:
    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=text,
    )


def publish_crew_result(
    *,
    client,
    channel_id: str,
    thread_ts: str,
    user_id: str,
    subject: str,
    post_count: int,
    content_style: str,
) -> None:
    """
    Run CrewAI and return its output to the originating Slack thread.
    """

    try:
        result = run_content_crew(
            subject=subject,
            post_count=post_count,
            content_style=content_style,
        )

        if not result:
            raise RuntimeError("CrewAI returned an empty result.")

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            "✅ Content generation completed.",
        )

        chunks = split_slack_message(result)

        for index, chunk in enumerate(chunks, start=1):
            header = ""

            if len(chunks) > 1:
                header = f"*Result {index}/{len(chunks)}*\n\n"

            post_thread_message(
                client,
                channel_id,
                thread_ts,
                f"{header}{chunk}",
            )

    except Exception as exc:
        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "❌ I could not generate the LinkedIn content.\n"
                f"Error: `{type(exc).__name__}: {exc}`"
            ),
        )

    finally:
        conversation_store.delete(
            channel_id,
            thread_ts,
            user_id,
        )


def start_generation(
    *,
    client,
    conversation: Conversation,
) -> None:
    if (
        not conversation.topic
        or conversation.post_count is None
        or not conversation.content_style
    ):
        raise ValueError("Conversation inputs are incomplete.")

    post_thread_message(
        client,
        conversation.channel_id,
        conversation.thread_ts,
        (
            "🚀 Starting the AI content crew.\n\n"
            f"*Topic:* {conversation.topic}\n"
            f"*Post options:* {conversation.post_count}\n"
            f"*Style:* {conversation.content_style}\n\n"
            "The completed content will be returned in this thread."
        ),
    )

    executor.submit(
        publish_crew_result,
        client=client,
        channel_id=conversation.channel_id,
        thread_ts=conversation.thread_ts,
        user_id=conversation.user_id,
        subject=conversation.topic,
        post_count=conversation.post_count,
        content_style=conversation.content_style,
    )


@app.event("app_mention")
def handle_app_mention(event, client, body, logger):
    """
    Start a new content-generation conversation when the bot is mentioned.
    """

    event_id = body.get("event_id")

    if not conversation_store.mark_event_processed(event_id):
        return

    channel_id = event["channel"]
    user_id = event["user"]
    message_ts = event["ts"]
    thread_ts = event.get("thread_ts") or message_ts
    supplied_text = remove_bot_mention(event.get("text", ""))

    conversation = conversation_store.create(
        channel_id=channel_id,
        thread_ts=thread_ts,
        user_id=user_id,
    )

    if supplied_text:
        conversation.topic = supplied_text
        conversation.step = "waiting_for_count"
        conversation_store.save(conversation)

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                f"Topic received: *{supplied_text}*\n\n"
                "How many LinkedIn post options should I generate?\n"
                "Reply with `1`, `3`, or `5`."
            ),
        )
        return

    post_thread_message(
        client,
        channel_id,
        thread_ts,
        (
            "What AI, Data Science, or AI Engineering topic "
            "should the LinkedIn post cover?"
        ),
    )


@app.event("message")
def handle_thread_reply(event, client, body, logger):
    """
    Continue conversations from replies inside the bot-created thread.
    """

    # Ignore messages created by bots and message-change events.
    if event.get("bot_id") or event.get("subtype"):
        return

    thread_ts = event.get("thread_ts")

    # Only process thread replies here.
    if not thread_ts:
        return

    event_id = body.get("event_id")

    if not conversation_store.mark_event_processed(event_id):
        return

    channel_id = event["channel"]
    user_id = event["user"]
    text = event.get("text", "").strip()

    conversation = conversation_store.get(
        channel_id,
        thread_ts,
        user_id,
    )

    if conversation is None:
        return

    if conversation.step == "waiting_for_topic":
        if not text:
            post_thread_message(
                client,
                channel_id,
                thread_ts,
                "Please provide a topic.",
            )
            return

        conversation.topic = text
        conversation.step = "waiting_for_count"
        conversation_store.save(conversation)

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "How many LinkedIn post options should I generate?\n"
                "Reply with `1`, `3`, or `5`."
            ),
        )
        return

    if conversation.step == "waiting_for_count":
        try:
            post_count = int(text)
        except ValueError:
            post_count = 0

        if post_count not in VALID_POST_COUNTS:
            post_thread_message(
                client,
                channel_id,
                thread_ts,
                "Please reply with `1`, `3`, or `5`.",
            )
            return

        conversation.post_count = post_count
        conversation.step = "waiting_for_style"
        conversation_store.save(conversation)

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "Which writing style should I use?\n\n"
                "• `Educational`\n"
                "• `Opinion`\n"
                "• `Practitioner`\n"
                "• `Mixed`"
            ),
        )
        return

    if conversation.step == "waiting_for_style":
        normalized_style = text.lower().strip()
        content_style = STYLE_ALIASES.get(normalized_style)

        if not content_style:
            post_thread_message(
                client,
                channel_id,
                thread_ts,
                (
                    "Please choose `Educational`, `Opinion`, "
                    "`Practitioner`, or `Mixed`."
                ),
            )
            return

        conversation.content_style = content_style
        conversation.step = "ready"
        conversation_store.save(conversation)

        start_generation(
            client=client,
            conversation=conversation,
        )


def main() -> None:
    print("Slack AI Content Bot is running in Socket Mode...")
    SocketModeHandler(
        app,
        SLACK_APP_TOKEN,
    ).start()

@app.event("app_mention")
def handle_app_mention(event, client, body, logger):
    print("APP MENTION RECEIVED:", event)

if __name__ == "__main__":
    main()