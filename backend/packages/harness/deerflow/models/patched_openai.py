"""Patched ChatOpenAI that preserves reasoning_content in multi-turn conversations.

This module provides a patched version of ChatOpenAI that properly handles
reasoning_content when sending messages back to the API. The original ChatOpenAI
discards reasoning_content during streaming chunk parsing AND during payload
construction. This patch fixes both:

1. _convert_chunk_to_generation_chunk: captures reasoning_content from streaming
   deltas into AIMessageChunk.additional_kwargs
2. _get_request_payload: backfills reasoning_content from additional_kwargs into
   the HTTP payload sent to the API

Without both fixes, models like Kimi that require reasoning_content on all
assistant messages in multi-turn conversations will reject the request.
"""

import logging
from typing import Any

from langchain_core.language_models import LanguageModelInput
from langchain_core.messages import AIMessage, AIMessageChunk
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


class PatchedChatOpenAI(ChatOpenAI):
    """ChatOpenAI with proper reasoning_content preservation.

    When using thinking/reasoning enabled models via OpenAI-compatible gateways,
    the API may expect reasoning_content to be present on ALL assistant messages
    in multi-turn conversations. This patched version ensures reasoning_content
    is captured from streaming responses and included in subsequent request payloads.
    """

    def _convert_chunk_to_generation_chunk(self, chunk: dict, *args: Any, **kwargs: Any) -> Any:
        """Capture reasoning_content from streaming chunks into additional_kwargs."""
        result = super()._convert_chunk_to_generation_chunk(chunk, *args, **kwargs)
        if result is None:
            return result

        # Extract reasoning_content from the streaming delta
        choices = chunk.get("choices") or chunk.get("chunk", {}).get("choices", [])
        if choices:
            delta = choices[0].get("delta") or {}
            reasoning_content = delta.get("reasoning_content")
            if reasoning_content is not None and isinstance(result.message, AIMessageChunk):
                result.message.additional_kwargs["reasoning_content"] = reasoning_content

        return result

    def _get_request_payload(
        self,
        input_: LanguageModelInput,
        *,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> dict:
        """Get request payload with reasoning_content preserved."""
        original_messages = self._convert_input(input_).to_messages()
        payload = super()._get_request_payload(input_, stop=stop, **kwargs)

        payload_messages = payload.get("messages", [])

        if len(payload_messages) == len(original_messages):
            for payload_msg, orig_msg in zip(payload_messages, original_messages):
                if payload_msg.get("role") == "assistant" and isinstance(orig_msg, AIMessage):
                    reasoning_content = orig_msg.additional_kwargs.get("reasoning_content")
                    if reasoning_content is not None:
                        payload_msg["reasoning_content"] = reasoning_content
        else:
            # Fallback: match by counting assistant messages
            ai_messages = [m for m in original_messages if isinstance(m, AIMessage)]
            assistant_payloads = [(i, m) for i, m in enumerate(payload_messages) if m.get("role") == "assistant"]

            for (idx, payload_msg), ai_msg in zip(assistant_payloads, ai_messages):
                reasoning_content = ai_msg.additional_kwargs.get("reasoning_content")
                if reasoning_content is not None:
                    payload_messages[idx]["reasoning_content"] = reasoning_content

        return payload
