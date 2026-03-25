"""IM Channel integration for Allo.

Provides a pluggable channel system that connects external messaging platforms
(Feishu/Lark, Slack, Telegram) to the Allo agent via the ChannelManager,
which uses ``langgraph-sdk`` to communicate with the underlying LangGraph Server.
"""

from app.channels.base import Channel
from app.channels.message_bus import InboundMessage, MessageBus, OutboundMessage

__all__ = [
    "Channel",
    "InboundMessage",
    "MessageBus",
    "OutboundMessage",
]
