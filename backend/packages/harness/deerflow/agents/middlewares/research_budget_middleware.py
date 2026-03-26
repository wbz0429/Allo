"""Middleware to enforce a research budget on web_search / web_fetch calls.

Prevents the agent from endlessly researching by tracking cumulative tool call
counts per user message and injecting warnings / hard-stopping when limits
are reached.

Unlike LoopDetectionMiddleware (which catches *identical* repeated calls), this
middleware counts *total* calls to specific tool names regardless of arguments.
It acts as a safety net — the SKILL.md instructs the model on per-level budgets,
while this middleware enforces an absolute ceiling.

Reset strategy: counters reset when a new HumanMessage is detected (i.e. the user
sent a new message). This works regardless of whether the middleware instance is
recreated per-run (LangGraph Server) or shared across runs (DeerFlowClient).
"""

import logging
from typing import override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import SystemMessage
from langgraph.runtime import Runtime

logger = logging.getLogger(__name__)

# Default budget limits (matches the "Deep" research level — the maximum)
_DEFAULT_MAX_SEARCHES = 20
_DEFAULT_MAX_FETCHES = 8

# Warn when usage reaches this fraction of the limit
_WARN_FRACTION = 0.8

# Tool names to track
_SEARCH_TOOL_NAMES = frozenset({"web_search"})
_FETCH_TOOL_NAMES = frozenset({"web_fetch"})

_WARNING_MSG_TEMPLATE = (
    "[RESEARCH BUDGET WARNING] You have used {used} out of {limit} {tool_type} calls. You are approaching the research budget limit. Wrap up your research and proceed to content generation. Do NOT start new search rounds."
)

_HARD_STOP_MSG_TEMPLATE = (
    "[RESEARCH BUDGET EXCEEDED] You have reached the maximum of {limit} {tool_type} calls. "
    "STOP all research immediately. Produce your final answer or content using the information "
    "you have already gathered. Any further {tool_type} calls will be blocked."
)


def _find_last_human_message_id(messages: list) -> str | None:
    """Walk messages backwards to find the ID of the last HumanMessage."""
    for msg in reversed(messages):
        if getattr(msg, "type", None) == "human":
            return getattr(msg, "id", None)
    return None


class ResearchBudgetMiddleware(AgentMiddleware[AgentState]):
    """Enforces per-user-message limits on web_search and web_fetch tool calls.

    Tracks cumulative usage and:
    - Resets counters when a new user message is detected
    - Injects a warning when usage reaches ~80% of the limit
    - Strips research tool calls when the hard limit is reached

    Args:
        max_searches: Maximum web_search calls per user message. Default: 20.
        max_fetches: Maximum web_fetch calls per user message. Default: 8.
    """

    def __init__(
        self,
        max_searches: int = _DEFAULT_MAX_SEARCHES,
        max_fetches: int = _DEFAULT_MAX_FETCHES,
    ):
        super().__init__()
        self.max_searches = max_searches
        self.max_fetches = max_fetches
        self._search_count = 0
        self._fetch_count = 0
        self._warned_search = False
        self._warned_fetch = False
        self._last_human_msg_id: str | None = None

    def _maybe_reset(self, messages: list) -> None:
        """Reset counters if a new user message is detected."""
        current_id = _find_last_human_message_id(messages)
        if current_id is None:
            return
        if self._last_human_msg_id is not None and current_id != self._last_human_msg_id:
            logger.info("Research budget reset (new user message detected)")
            self._search_count = 0
            self._fetch_count = 0
            self._warned_search = False
            self._warned_fetch = False
        self._last_human_msg_id = current_id

    def _apply(self, state: AgentState, runtime: Runtime) -> dict | None:
        messages = state.get("messages", [])
        if not messages:
            return None

        last_msg = messages[-1]
        if getattr(last_msg, "type", None) != "ai":
            return None

        tool_calls = getattr(last_msg, "tool_calls", None)
        if not tool_calls:
            return None

        # Count research tool calls in this response
        new_searches = sum(1 for tc in tool_calls if tc.get("name") in _SEARCH_TOOL_NAMES)
        new_fetches = sum(1 for tc in tool_calls if tc.get("name") in _FETCH_TOOL_NAMES)

        if new_searches == 0 and new_fetches == 0:
            return None

        # Reset if user sent a new message since last check
        self._maybe_reset(messages)

        self._search_count += new_searches
        self._fetch_count += new_fetches

        # Check hard limits — strip research tool calls if exceeded
        search_exceeded = self._search_count > self.max_searches
        fetch_exceeded = self._fetch_count > self.max_fetches

        if search_exceeded or fetch_exceeded:
            logger.error(
                "Research budget exceeded — stripping research tool calls (search: %d/%d, fetch: %d/%d)",
                self._search_count,
                self.max_searches,
                self._fetch_count,
                self.max_fetches,
            )

            blocked_names = _SEARCH_TOOL_NAMES | _FETCH_TOOL_NAMES
            filtered_tool_calls = [tc for tc in tool_calls if tc.get("name") not in blocked_names]

            stop_msg = _HARD_STOP_MSG_TEMPLATE.format(
                limit=f"{self.max_searches} search / {self.max_fetches} fetch",
                tool_type="research",
            )

            updated_msg = last_msg.model_copy(
                update={
                    "tool_calls": filtered_tool_calls,
                    "content": (last_msg.content or "") + f"\n\n{stop_msg}",
                }
            )
            return {"messages": [updated_msg]}

        # Check warning thresholds
        warning_parts = []

        if not self._warned_search and self._search_count >= int(self.max_searches * _WARN_FRACTION):
            self._warned_search = True
            warning_parts.append(_WARNING_MSG_TEMPLATE.format(used=self._search_count, limit=self.max_searches, tool_type="web_search"))

        if not self._warned_fetch and self._fetch_count >= int(self.max_fetches * _WARN_FRACTION):
            self._warned_fetch = True
            warning_parts.append(_WARNING_MSG_TEMPLATE.format(used=self._fetch_count, limit=self.max_fetches, tool_type="web_fetch"))

        if warning_parts:
            return {"messages": [SystemMessage(content="\n\n".join(warning_parts))]}

        return None

    @override
    def after_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)

    @override
    async def aafter_model(self, state: AgentState, runtime: Runtime) -> dict | None:
        return self._apply(state, runtime)
