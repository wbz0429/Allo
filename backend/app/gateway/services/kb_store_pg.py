"""Postgres-backed implementation of the harness KnowledgeBaseStore."""

import re

from sqlalchemy import select

from app.gateway.db.models import KnowledgeBase, KnowledgeDocument
from app.gateway.rag.embedder import embed_text
from deerflow.config.paths import get_paths
from deerflow.stores import KnowledgeBaseStore


class PostgresKBStore(KnowledgeBaseStore):
    """Persist knowledge base operations via gateway Postgres tables."""

    def __init__(self, async_session_factory) -> None:
        self._async_session_factory = async_session_factory

    async def list_documents(self, kb_id: str) -> list[dict]:
        async with self._async_session_factory() as session:
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id).order_by(KnowledgeDocument.created_at.desc())
            result = await session.execute(stmt)
            return [
                {
                    "id": doc.id,
                    "filename": doc.filename,
                    "content_type": doc.content_type,
                    "file_size": doc.file_size or 0,
                    "index_status": doc.index_status or "none",
                    "status": doc.status,
                }
                for doc in result.scalars().all()
            ]

    async def read_document(self, kb_id: str, filename: str) -> str | None:
        async with self._async_session_factory() as session:
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id == kb_id, KnowledgeDocument.filename == filename)
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc is None:
                return None

            content = doc.content_md
            if not content and doc.markdown_path:
                md_file = get_paths().base_dir / doc.markdown_path
                if md_file.exists():
                    content = md_file.read_text(encoding="utf-8")
            return content or ""

    async def keyword_search(self, kb_ids: list[str], query: str, top_k: int = 5) -> list[dict]:
        if not query.strip():
            return []

        async with self._async_session_factory() as session:
            stmt = select(KnowledgeDocument).where(KnowledgeDocument.kb_id.in_(kb_ids), KnowledgeDocument.content_md.ilike(f"%{query}%"))
            result = await session.execute(stmt)

            results = []
            for doc in result.scalars().all():
                content = doc.content_md or ""
                count = len(re.findall(re.escape(query), content, re.IGNORECASE))
                match = re.search(re.escape(query), content, re.IGNORECASE)
                if match:
                    start = max(0, match.start() - 200)
                    end = min(len(content), match.end() + 200)
                    snippet = content[start:end]
                else:
                    snippet = content[:400]
                results.append({"doc_id": doc.id, "filename": doc.filename, "snippet": snippet, "score": float(count)})

            results.sort(key=lambda r: r["score"], reverse=True)
            return results[:top_k]

    async def semantic_search(self, kb_ids: list[str], query: str, top_k: int = 5) -> list[dict]:
        async with self._async_session_factory() as session:
            query_embedding = await embed_text(query)

            all_results = []
            for kb_id in kb_ids:
                from app.gateway.rag.retriever import search_chunks

                chunks = await search_chunks(session, query_embedding, kb_id, top_k=top_k)
                all_results.extend(chunks)

            all_results.sort(key=lambda r: r.get("score", 0), reverse=True)
            return all_results[:top_k]

    async def list_knowledge_bases(self, org_id: str) -> list[dict]:
        async with self._async_session_factory() as session:
            stmt = select(KnowledgeBase).where(KnowledgeBase.org_id == org_id).order_by(KnowledgeBase.created_at.desc())
            result = await session.execute(stmt)
            return [
                {
                    "id": kb.id,
                    "name": kb.name,
                    "description": kb.description,
                }
                for kb in result.scalars().all()
            ]
