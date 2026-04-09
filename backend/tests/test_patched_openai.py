"""Tests for PatchedChatOpenAI reasoning_content preservation."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from deerflow.models.patched_openai import PatchedChatOpenAI


def _make_ai_message(content: str, *, reasoning_content: str | None = None, tool_calls: list | None = None) -> AIMessage:
    additional_kwargs = {}
    if reasoning_content is not None:
        additional_kwargs["reasoning_content"] = reasoning_content
    return AIMessage(content=content, additional_kwargs=additional_kwargs, tool_calls=tool_calls or [])


class TestPatchedChatOpenAI:
    """Tests for reasoning_content backfill in _get_request_payload."""

    def _call_get_request_payload(self, messages: list) -> dict:
        """Helper: invoke _get_request_payload with mocked parent behaviour."""
        model = PatchedChatOpenAI(model="test", api_key="fake")

        # Build payload messages that the parent would produce (no reasoning_content)
        payload_messages = []
        for msg in messages:
            if isinstance(msg, HumanMessage):
                payload_messages.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                d: dict = {"role": "assistant", "content": msg.content}
                if msg.tool_calls:
                    d["tool_calls"] = [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": "{}"}} for tc in msg.tool_calls]
                payload_messages.append(d)
            elif isinstance(msg, ToolMessage):
                payload_messages.append({"role": "tool", "content": msg.content, "tool_call_id": msg.tool_call_id})

        parent_payload = {"model": "test", "messages": payload_messages}

        with patch.object(PatchedChatOpenAI, "_convert_input") as mock_convert:
            mock_prompt_value = MagicMock()
            mock_prompt_value.to_messages.return_value = messages
            mock_convert.return_value = mock_prompt_value

            with patch("langchain_openai.ChatOpenAI._get_request_payload", return_value=parent_payload):
                return model._get_request_payload(messages)

    def test_backfills_reasoning_content_on_assistant_messages(self):
        messages = [
            HumanMessage(content="hello"),
            _make_ai_message("thinking response", reasoning_content="I thought about this"),
            HumanMessage(content="follow up"),
        ]

        payload = self._call_get_request_payload(messages)

        ai_payload = payload["messages"][1]
        assert ai_payload["reasoning_content"] == "I thought about this"

    def test_backfills_reasoning_content_on_tool_call_messages(self):
        messages = [
            HumanMessage(content="read the file"),
            _make_ai_message(
                "I'll read that",
                reasoning_content="Let me think about which file",
                tool_calls=[{"id": "call_1", "name": "read_file", "args": {"path": "/tmp/test"}}],
            ),
            ToolMessage(content="file contents here", tool_call_id="call_1", name="read_file"),
            HumanMessage(content="now what?"),
        ]

        payload = self._call_get_request_payload(messages)

        ai_payload = payload["messages"][1]
        assert ai_payload["reasoning_content"] == "Let me think about which file"
        # Tool message should be untouched
        assert payload["messages"][2]["content"] == "file contents here"

    def test_no_op_when_no_reasoning_content(self):
        messages = [
            HumanMessage(content="hello"),
            _make_ai_message("response"),
            HumanMessage(content="follow up"),
        ]

        payload = self._call_get_request_payload(messages)

        ai_payload = payload["messages"][1]
        assert "reasoning_content" not in ai_payload

    def test_preserves_none_reasoning_content(self):
        """None reasoning_content should not be backfilled (only non-None values)."""
        messages = [
            HumanMessage(content="hello"),
            AIMessage(content="response", additional_kwargs={"reasoning_content": None}),
        ]

        payload = self._call_get_request_payload(messages)

        ai_payload = payload["messages"][1]
        # None should not be backfilled
        assert "reasoning_content" not in ai_payload

    def test_multiple_assistant_messages_with_mixed_reasoning(self):
        messages = [
            HumanMessage(content="q1"),
            _make_ai_message("a1", reasoning_content="thought 1"),
            HumanMessage(content="q2"),
            _make_ai_message("a2"),  # no reasoning
            HumanMessage(content="q3"),
            _make_ai_message("a3", reasoning_content="thought 3"),
        ]

        payload = self._call_get_request_payload(messages)

        assert payload["messages"][1]["reasoning_content"] == "thought 1"
        assert "reasoning_content" not in payload["messages"][3]
        assert payload["messages"][5]["reasoning_content"] == "thought 3"
