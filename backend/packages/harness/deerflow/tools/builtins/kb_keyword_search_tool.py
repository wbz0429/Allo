"""Knowledge base keyword search tool — full-text search without index."""

from langchain.tools import tool
from langchain_core.runnables import ensure_config

from deerflow.context import get_user_context
from deerflow.store_registry import get_store


@tool("knowledge_base_keyword_search", parse_docstring=True)
def knowledge_base_keyword_search_tool(query: str, top_k: int = 5) -> str:
    """Full-text keyword search across all knowledge base documents.

    Always available (no index needed). Use when searching for specific terms or phrases.
    Automatically searches across all available knowledge bases.

    Args:
        query: The keyword or phrase to search for.
        top_k: Maximum number of results to return.
    """
    from deerflow.stores import KnowledgeBaseStore

    store = get_store("kb")
    if not isinstance(store, KnowledgeBaseStore):
        return "Knowledge base store not available."

    ctx = get_user_context(ensure_config())
    if ctx is None or not ctx.org_id:
        return "Cannot determine organization context."

    import asyncio
    import concurrent.futures

    async def _search_all():
        kbs = await store.list_knowledge_bases(ctx.org_id)
        kb_ids = [kb["id"] for kb in kbs]
        if not kb_ids:
            return []
        return await store.keyword_search(kb_ids, query, top_k)

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
        return f"No results found for '{query}'."

    lines = []
    for r in results:
        lines.append(f"**{r['filename']}** (matches: {r.get('score', 0):.0f})")
        lines.append(r.get("snippet", "")[:500])
        lines.append("")
    return "\n".join(lines)
