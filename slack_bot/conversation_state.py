from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock
from typing import Literal


ConversationStep = Literal[
    "waiting_for_topic",
    "waiting_for_count",
    "waiting_for_style",
    "ready",
]


@dataclass
class Conversation:
    channel_id: str
    thread_ts: str
    user_id: str
    step: ConversationStep = "waiting_for_topic"
    topic: str | None = None
    post_count: int | None = None
    content_style: str | None = None
    processed_event_ids: set[str] = field(default_factory=set)


class ConversationStore:
    """
    In-memory conversation storage.

    This is suitable for local development. We will replace it with SQLite
    after the Slack workflow works correctly.
    """

    def __init__(self) -> None:
        self._conversations: dict[str, Conversation] = {}
        self._processed_events: set[str] = set()
        self._lock = Lock()

    @staticmethod
    def make_key(channel_id: str, thread_ts: str, user_id: str) -> str:
        return f"{channel_id}:{thread_ts}:{user_id}"

    def create(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
    ) -> Conversation:
        key = self.make_key(channel_id, thread_ts, user_id)

        conversation = Conversation(
            channel_id=channel_id,
            thread_ts=thread_ts,
            user_id=user_id,
        )

        with self._lock:
            self._conversations[key] = conversation

        return conversation

    def get(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
    ) -> Conversation | None:
        key = self.make_key(channel_id, thread_ts, user_id)

        with self._lock:
            return self._conversations.get(key)

    def save(self, conversation: Conversation) -> None:
        key = self.make_key(
            conversation.channel_id,
            conversation.thread_ts,
            conversation.user_id,
        )

        with self._lock:
            self._conversations[key] = conversation

    def delete(
        self,
        channel_id: str,
        thread_ts: str,
        user_id: str,
    ) -> None:
        key = self.make_key(channel_id, thread_ts, user_id)

        with self._lock:
            self._conversations.pop(key, None)

    def mark_event_processed(self, event_id: str | None) -> bool:
        """
        Returns False when the event was already processed.
        """

        if not event_id:
            return True

        with self._lock:
            if event_id in self._processed_events:
                return False

            self._processed_events.add(event_id)
            return True


conversation_store = ConversationStore()