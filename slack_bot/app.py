from __future__ import annotations

import os
import re
from concurrent.futures import ThreadPoolExecutor

from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler


# Load .env before importing content_memory because it needs OPENAI_API_KEY.
load_dotenv()

from memory.content_memory import content_memory
from slack_bot.conversation_state import Conversation, conversation_store
from slack_bot.crew_runner import run_content_crew


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

executor = ThreadPoolExecutor(max_workers=4)


def remove_bot_mention(text: str) -> str:
    """
    Remove Slack bot mention markup such as <@U123ABC>.
    """

    return re.sub(r"<@[A-Z0-9]+>", "", text).strip()


def split_slack_message(
    text: str,
    max_length: int = 3500,
) -> list[str]:
    """
    Split long CrewAI output into Slack-safe message chunks.
    """

    text = text.strip()

    if not text:
        return []

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
    """
    Post a normal text message inside a Slack thread.
    """

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text=text,
    )


def get_action_context(
    body,
) -> tuple[str, str, str]:
    """
    Read channel, thread and user details from a Slack button event.
    """

    channel_id = body["channel"]["id"]
    user_id = body["user"]["id"]

    message = body["message"]

    thread_ts = (
        message.get("thread_ts")
        or message["ts"]
    )

    return channel_id, thread_ts, user_id


def post_count_question(
    client,
    channel_id: str,
    thread_ts: str,
) -> None:
    """
    Ask the user how many LinkedIn post options they want.
    """

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text="How many LinkedIn post options should I generate?",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*How many LinkedIn post options "
                        "should I generate?*"
                    ),
                },
            },
            {
                "type": "actions",
                "block_id": "post_count_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "1",
                        },
                        "value": "1",
                        "action_id": "select_post_count_1",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "3",
                        },
                        "value": "3",
                        "action_id": "select_post_count_3",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "5",
                        },
                        "value": "5",
                        "action_id": "select_post_count_5",
                    },
                ],
            },
        ],
    )


def post_style_question(
    client,
    channel_id: str,
    thread_ts: str,
) -> None:
    """
    Ask the user which LinkedIn writing style they want.
    """

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text="Which writing style should I use?",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*Which writing style should I use?*",
                },
            },
            {
                "type": "actions",
                "block_id": "content_style_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Educational",
                        },
                        "value": "Educational",
                        "action_id": "select_style_educational",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Opinion",
                        },
                        "value": "Opinion",
                        "action_id": "select_style_opinion",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Practitioner",
                        },
                        "value": "Practitioner Insight",
                        "action_id": "select_style_practitioner",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Mixed",
                        },
                        "value": "Mixed",
                        "action_id": "select_style_mixed",
                    },
                ],
            },
        ],
    )


def post_save_question(
    client,
    channel_id: str,
    thread_ts: str,
) -> None:
    """
    Ask whether the generated content should be saved in Chroma.
    """

    client.chat_postMessage(
        channel=channel_id,
        thread_ts=thread_ts,
        text="Would you like to save this generated content?",
        blocks=[
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        "*Would you like to save this content?*\n\n"
                        "Saved content will help prevent similar "
                        "future posts."
                    ),
                },
            },
            {
                "type": "actions",
                "block_id": "content_save_actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Save",
                        },
                        "style": "primary",
                        "value": "save",
                        "action_id": "save_generated_content",
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Don't save",
                        },
                        "value": "dont_save",
                        "action_id": "dont_save_generated_content",
                    },
                ],
            },
        ],
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
    memory_context: str,
) -> None:
    """
    Run CrewAI, return its output to Slack and ask whether to save it.
    """

    try:
        post_thread_message(
            client,
            channel_id,
            thread_ts,
            "🔎 Researching the topic and preparing the LinkedIn content...",
        )
        result = run_content_crew(
            subject=subject,
            post_count=post_count,
            content_style=content_style,
            memory_context=memory_context,
        )

        if not result:
            raise RuntimeError("CrewAI returned an empty result.")

        conversation = conversation_store.get(
            channel_id,
            thread_ts,
            user_id,
        )

        if conversation is None:
            raise RuntimeError(
                "Conversation state could not be found."
            )

        # Keep generated content until Save or Don't save is clicked.
        conversation.generated_content = result
        conversation_store.save(conversation)

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
                header = (
                    f"*Result {index}/{len(chunks)}*\n\n"
                )

            post_thread_message(
                client,
                channel_id,
                thread_ts,
                f"{header}{chunk}",
            )

        post_save_question(
            client,
            channel_id,
            thread_ts,
        )

    except Exception as exc:
        print("CREWAI ERROR:", repr(exc))

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "❌ I could not generate the LinkedIn content.\n"
                f"Error: `{type(exc).__name__}: {exc}`"
            ),
        )

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
    """
    Silently check Chroma memory and then start CrewAI.
    """

    if (
        not conversation.topic
        or conversation.post_count is None
        or not conversation.content_style
    ):
        raise ValueError("Conversation inputs are incomplete.")

    try:
        memory_context = content_memory.get_memory_context(
            topic=conversation.topic,
            content_style=conversation.content_style,
            limit=15,
        )

    except Exception as exc:
        # Memory failure should not stop normal content generation.
        print("CONTENT MEMORY ERROR:", repr(exc))

        memory_context = (
            "Content memory was unavailable. "
            "Create original content and avoid generic repetition."
        )

    conversation.memory_context = memory_context
    conversation_store.save(conversation)

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
        memory_context=memory_context,
    )


def save_content_in_background(
    *,
    client,
    channel_id: str,
    thread_ts: str,
    user_id: str,
) -> None:
    """
    Generate metadata and save approved content in Chroma.
    """

    try:
        conversation = conversation_store.get(
            channel_id,
            thread_ts,
            user_id,
        )

        if conversation is None:
            raise RuntimeError("Conversation could not be found.")

        if not conversation.generated_content:
            raise RuntimeError(
                "No generated content is available to save."
            )

        if not conversation.topic:
            raise RuntimeError("Original topic is missing.")

        if conversation.post_count is None:
            raise RuntimeError("Post count is missing.")

        if not conversation.content_style:
            raise RuntimeError("Content style is missing.")

        saved_record = content_memory.save_post(
            topic=conversation.topic,
            content=conversation.generated_content,
            content_style=conversation.content_style,
            post_count=conversation.post_count,
            slack_channel_id=channel_id,
            slack_thread_ts=thread_ts,
            slack_user_id=user_id,
        )

        concepts = ", ".join(
            saved_record["concepts"]
        )

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "✅ *Content saved.*\n\n"
                f"*Headline:* {saved_record['headline']}\n\n"
                f"*Summary:* {saved_record['summary']}\n\n"
                f"*Angle:* "
                f"{saved_record['content_angle']}\n\n"
                f"*Concepts:* "
                f"{concepts or 'Not specified'}\n\n"
                f"*Total saved records:* "
                f"{content_memory.count_saved_posts()}"
            ),
        )

    except Exception as exc:
        print("CONTENT SAVE ERROR:", repr(exc))

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "❌ I could not save the generated content.\n"
                f"Error: `{type(exc).__name__}: {exc}`"
            ),
        )

    finally:
        conversation_store.delete(
            channel_id,
            thread_ts,
            user_id,
        )


@app.event("app_mention")
def handle_app_mention(event, client, body, logger):
    """
    Start a new workflow when the Slack bot is mentioned.
    """

    event_id = body.get("event_id")

    if not conversation_store.mark_event_processed(event_id):
        return

    channel_id = event["channel"]
    user_id = event["user"]
    message_ts = event["ts"]

    thread_ts = (
        event.get("thread_ts")
        or message_ts
    )

    supplied_text = remove_bot_mention(
        event.get("text", "")
    )

    print("\nAPP MENTION RECEIVED")
    print("CHANNEL:", channel_id)
    print("USER:", user_id)
    print("THREAD:", thread_ts)
    print("TOPIC:", repr(supplied_text))

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
            f"Topic received: *{supplied_text}*",
        )

        post_count_question(
            client,
            channel_id,
            thread_ts,
        )

        return

    post_thread_message(
        client,
        channel_id,
        thread_ts,
        (
            "Please mention me again and include the topic "
            "in the same message.\n\n"
            "Example:\n"
            "`@CrewAI Notifications Production RAG evaluation`"
        ),
    )

    conversation_store.delete(
        channel_id,
        thread_ts,
        user_id,
    )


@app.action(re.compile(r"^select_post_count_(1|3|5)$"))
def handle_post_count_selection(
    ack,
    body,
    client,
    logger,
):
    """
    Save selected post count and ask for writing style.
    """

    ack()

    try:
        action = body["actions"][0]
        post_count = int(action["value"])

        channel_id, thread_ts, user_id = (
            get_action_context(body)
        )

        conversation = conversation_store.get(
            channel_id,
            thread_ts,
            user_id,
        )

        if conversation is None:
            post_thread_message(
                client,
                channel_id,
                thread_ts,
                (
                    "⚠️ This conversation has expired.\n"
                    "Mention me again to start a new request."
                ),
            )
            return

        conversation.post_count = post_count
        conversation.step = "waiting_for_style"

        conversation_store.save(conversation)

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            f"Post options selected: *{post_count}*",
        )

        post_style_question(
            client,
            channel_id,
            thread_ts,
        )

    except Exception as exc:
        logger.exception(
            "Failed to process post count selection"
        )

        print("POST COUNT ERROR:", repr(exc))


@app.action(re.compile(r"^select_style_"))
def handle_style_selection(
    ack,
    body,
    client,
    logger,
):
    """
    Save selected style and start the original generation flow.
    """

    ack()

    try:
        action = body["actions"][0]
        content_style = action["value"]

        channel_id, thread_ts, user_id = (
            get_action_context(body)
        )

        conversation = conversation_store.get(
            channel_id,
            thread_ts,
            user_id,
        )

        if conversation is None:
            post_thread_message(
                client,
                channel_id,
                thread_ts,
                (
                    "⚠️ This conversation has expired.\n"
                    "Mention me again to start a new request."
                ),
            )
            return

        conversation.content_style = content_style
        conversation.step = "ready"

        conversation_store.save(conversation)

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            f"Writing style selected: *{content_style}*",
        )

        # Original flow continues here.
        # Chroma memory checking happens silently inside start_generation.
        start_generation(
            client=client,
            conversation=conversation,
        )

    except Exception as exc:
        logger.exception(
            "Failed to process style selection"
        )

        print("STYLE ERROR:", repr(exc))


@app.action("save_generated_content")
def handle_save_generated_content(
    ack,
    body,
    client,
    logger,
):
    """
    Save generated content after user approval.
    """

    ack()

    try:
        channel_id, thread_ts, user_id = (
            get_action_context(body)
        )

        conversation = conversation_store.get(
            channel_id,
            thread_ts,
            user_id,
        )

        if conversation is None:
            post_thread_message(
                client,
                channel_id,
                thread_ts,
                (
                    "⚠️ This generated content is no longer "
                    "available in the current session."
                ),
            )
            return

        post_thread_message(
            client,
            channel_id,
            thread_ts,
            (
                "💾 Saving the post and generating its "
                "headline and summary..."
            ),
        )

        executor.submit(
            save_content_in_background,
            client=client,
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
        )

    except Exception as exc:
        logger.exception(
            "Failed to start content saving"
        )

        print("SAVE ACTION ERROR:", repr(exc))


@app.action("dont_save_generated_content")
def handle_dont_save_generated_content(
    ack,
    body,
    client,
    logger,
):
    """
    Discard content from the temporary conversation state.
    """

    ack()

    channel_id, thread_ts, user_id = (
        get_action_context(body)
    )

    conversation_store.delete(
        channel_id,
        thread_ts,
        user_id,
    )

    post_thread_message(
        client,
        channel_id,
        thread_ts,
        (
            "Content was not saved. It will not be used "
            "for future similarity checks."
        ),
    )


def main() -> None:
    print("Slack AI Content Bot is running in Socket Mode...")

    print(
        "Approved posts currently stored:",
        content_memory.count_saved_posts(),
    )

    SocketModeHandler(
        app,
        SLACK_APP_TOKEN,
    ).start()


if __name__ == "__main__":
    main()