"""Knowledge base semantic search tool — requires indexed documents."""

from langchain.tools import tool

from deerflow.context import get_user_context
from deerflow.store_registry import get_store


@tool("knowledge_base_search", parse_docstring=True)
def knowledge_base_search_tool(query: str, top_k: int = 5) -> str:
    """Semantic search across all indexed knowledge base documents.

    Only works on documents that have been indexed (embeddings generated).
    If no results, try knowledge_base_keyword_search or knowledge_base_read instead.
    Automatically searches across all available knowledge bases.

    Args:
        query: The search query for semantic matching.
        top_k: Maximum number of results to return.
    """
    from deerflow.stores import KnowledgeBaseStore

    store = get_store("kb")
    if not isinstance(store, KnowledgeBaseStore):
        return "Knowledge base store not available."

    ctx = get_user_context()
    if ctx is None or not ctx.org_id:
        return "Cannot determine organization context."

    import asyncio
    import concurrent.futures

    async def _search_all():
        kbs = await store.list_knowledge_bases(ctx.org_id)
        kb_ids = [kb["id"] for kb in kbs]
        if not kb_ids:
            return []
        return await store.semantic_search(kb_ids, query, top_k)

    def _run():
        return asyncio.run(_search_all())

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        results = asyncio.run(_search_all())
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            results = pool.submit(_run).result()

    if not results:
        return (
            f"No semantic search results for '{query}'. "
            "Documents may not be indexed yet. "
            "Try knowledge_base_keyword_search or knowledge_base_read instead."
        )

    lines = []
    for r in results:
        lines.append(f"**Score: {r.get('score', 0):.3f}** (doc: {r.get('doc_id', 'unknown')})")
        lines.append(r.get("content", "")[:500])
        lines.append("")
    return "\n".join(lines)
