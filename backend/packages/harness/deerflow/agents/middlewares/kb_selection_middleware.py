"""Middleware to inject selected knowledge base hints into the current message."""

from __future__ import annotations

import asyncio
import concurrent.futures
import logging
from typing import NotRequired, override

from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain_core.messages import HumanMessage
from langgraph.runtime import Runtime

from deerflow.context import get_user_context
from deerflow.store_registry import get_store
from deerflow.stores import KnowledgeBaseStore

logger = logging.getLogger(__name__)


class KnowledgeBaseSelectionMiddlewareState(AgentState):
    selected_knowledge_bases: NotRequired[list[dict] | None]


class KnowledgeBaseSelectionMiddleware(AgentMiddleware[KnowledgeBaseSelectionMiddlewareState]):
    """Prepend selected knowledge base summaries to the last human message."""

    state_schema = KnowledgeBaseSelectionMiddlewareState

    def __init__(self, base_dir: str | None = None):
        super().__init__()

    def _selected_from_kwargs(self, message: HumanMessage) -> list[dict] | None:
        selected = (message.additional_kwargs or {}).get("knowledge_bases")
        if not isinstance(selected, list) or not selected:
            return None

        normalized: list[dict] = []
        for item in selected:
            if not isinstance(item, dict):
                continue
            kb_id = item.get("id")
            kb_name = item.get("name")
            if isinstance(kb_id, str) and kb_id.strip() and isinstance(kb_name, str) and kb_name.strip():
                normalized.append({"id": kb_id.strip(), "name": kb_name.strip()})
        return normalized or None

    def _resolve_selected_kbs(self, org_id: str, selected: list[dict]) -> list[dict] | None:
        store = get_store("kb")
        if not isinstance(store, KnowledgeBaseStore):
            return None

        selected_by_id = {item["id"]: item for item in selected}

        async def _load() -> list[dict]:
            all_kbs = await store.list_knowledge_bases(org_id)
            return [kb for kb in all_kbs if kb.get("id") in selected_by_id]

        def _run() -> list[dict]:
            return asyncio.run(_load())

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(_load())
        else:
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                return pool.submit(_run).result()

    def _build_selected_kb_message(self, selected: list[dict], resolved: list[dict] | None) -> str:
        lines = ["<selected_knowledge_bases>", "用户当前明确选择了这些知识库，请优先参考它们：", ""]

        if resolved:
            for kb in resolved:
                desc = f" ({kb['description']})" if kb.get("description") else ""
                docs = kb.get("documents", [])
                if docs:
                    doc_list = ", ".join(docs[:20])
                    if len(docs) > 20:
                        doc_list += f" ... and {len(docs) - 20} more"
                    lines.append(f"- **{kb['name']}**{desc} — {len(docs)} files: {doc_list}")
                else:
                    lines.append(f"- **{kb['name']}**{desc} — empty")
        else:
            for kb in selected:
                lines.append(f"- **{kb['name']}**")
            lines.append("")
            lines.append("当前还没有拿到这些知识库的文件清单，但你仍应优先考虑它们。")

        lines.extend(
            [
                "",
                "如果这些知识库不足以回答问题，你仍然可以继续使用知识库工具查看其他知识库。",
                "你无法直接看到文档内容，必须调用知识库工具才能读取具体文档。",
                "</selected_knowledge_bases>",
            ]
        )
        return "\n".join(lines)

    @override
    def before_agent(self, state: KnowledgeBaseSelectionMiddlewareState, runtime: Runtime) -> dict | None:
        messages = list(state.get("messages", []))
        if not messages:
            return None

        last_message = messages[-1]
        if not isinstance(last_message, HumanMessage):
            return None

        selected = self._selected_from_kwargs(last_message)
        if not selected:
            return None

        ctx = get_user_context(getattr(runtime, "config", None) or {})
        resolved = self._resolve_selected_kbs(ctx.org_id, selected) if ctx is not None and ctx.org_id else None
        logger.info(
            "KB selection injected into prompt: selected_ids=%s selected_names=%s resolved_count=%s org_id=%s",
            [kb["id"] for kb in selected],
            [kb["name"] for kb in selected],
            len(resolved or []),
            ctx.org_id if ctx is not None else None,
        )
        kb_message = self._build_selected_kb_message(selected, resolved)

        original_content = ""
        if isinstance(last_message.content, str):
            original_content = last_message.content
        elif isinstance(last_message.content, list):
            text_parts = []
            for block in last_message.content:
                if isinstance(block, dict) and block.get("type") == "text":
                    text_parts.append(block.get("text", ""))
            original_content = "\n".join(text_parts)

        updated_message = HumanMessage(
            content=f"{kb_message}\n\n{original_content}",
            id=last_message.id,
            additional_kwargs=last_message.additional_kwargs,
        )
        messages[-1] = updated_message

        return {
            "selected_knowledge_bases": selected,
            "messages": messages,
        }
