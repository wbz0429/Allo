from pathlib import Path
from types import SimpleNamespace

from langchain_core.messages import HumanMessage

from deerflow.agents.middlewares.kb_selection_middleware import KnowledgeBaseSelectionMiddleware
from deerflow.stores import KnowledgeBaseStore


class _FakeKBStore(KnowledgeBaseStore):
    def __init__(self, kbs: list[dict]):
        self._kbs = kbs

    async def list_documents(self, kb_id: str) -> list[dict]:
        return []

    async def read_document(self, kb_id: str, filename: str) -> str | None:
        return None

    async def keyword_search(self, kb_ids: list[str], query: str, top_k: int = 5) -> list[dict]:
        return []

    async def semantic_search(self, kb_ids: list[str], query: str, top_k: int = 5) -> list[dict]:
        return []

    async def list_knowledge_bases(self, org_id: str) -> list[dict]:
        return self._kbs


def _runtime(*, user_id: str = "user-1", org_id: str = "org-1") -> SimpleNamespace:
    return SimpleNamespace(
        context={"thread_id": "thread-1"},
        config={"configurable": {"user_id": user_id, "org_id": org_id}},
    )


def _human_with_kbs(content: str, knowledge_bases: list[dict]) -> HumanMessage:
    return HumanMessage(content=content, additional_kwargs={"knowledge_bases": knowledge_bases})


def test_before_agent_injects_selected_kb_documents(monkeypatch, tmp_path: Path) -> None:
    middleware = KnowledgeBaseSelectionMiddleware(base_dir=str(tmp_path))
    store = _FakeKBStore(
        [
            {"id": "kb-2", "name": "Handbook", "description": "ops", "documents": ["runbook.md", "faq.md"]},
            {"id": "kb-1", "name": "Contracts", "description": "legal", "documents": ["msa.md", "sla.md"]},
        ]
    )
    monkeypatch.setattr("deerflow.agents.middlewares.kb_selection_middleware.get_store", lambda name: store)

    state = {
        "messages": [
            _human_with_kbs(
                "请先看合同知识库再回答",
                [{"id": "kb-1", "name": "Contracts"}],
            )
        ]
    }

    result = middleware.before_agent(state, _runtime())

    assert result is not None
    updated = result["messages"][-1]
    assert "<selected_knowledge_bases>" in updated.content
    assert "用户当前明确选择了这些知识库，请优先参考它们" in updated.content
    assert "**Contracts** (legal)" in updated.content
    assert "msa.md, sla.md" in updated.content
    assert "如果这些知识库不足以回答问题，你仍然可以继续使用知识库工具查看其他知识库" in updated.content
    assert updated.additional_kwargs == {"knowledge_bases": [{"id": "kb-1", "name": "Contracts"}]}


def test_before_agent_falls_back_to_selected_names_when_store_unavailable(tmp_path: Path) -> None:
    middleware = KnowledgeBaseSelectionMiddleware(base_dir=str(tmp_path))
    state = {
        "messages": [
            _human_with_kbs(
                "先看这个库",
                [{"id": "kb-9", "name": "Playbooks"}],
            )
        ]
    }

    result = middleware.before_agent(state, _runtime())

    assert result is not None
    updated = result["messages"][-1]
    assert "<selected_knowledge_bases>" in updated.content
    assert "**Playbooks**" in updated.content
    assert "当前还没有拿到这些知识库的文件清单" in updated.content


def test_before_agent_returns_none_without_selected_kbs(tmp_path: Path) -> None:
    middleware = KnowledgeBaseSelectionMiddleware(base_dir=str(tmp_path))
    state = {"messages": [HumanMessage(content="hello")]}

    assert middleware.before_agent(state, _runtime()) is None
