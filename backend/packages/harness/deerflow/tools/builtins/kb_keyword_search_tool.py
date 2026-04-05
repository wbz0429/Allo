"""Knowledge base keyword search tool — full-text search without index."""

from langchain.tools import tool

from deerflow.store_registry import get_store


@tool("knowledge_base_keyword_search", parse_docstring=True)
def knowledge_base_keyword_search_tool(query: str, kb_ids: list[str], top_k: int = 5) -> str:
    """Full-text keyword search across knowledge base documents.

    Always available (no index needed). Use when searching for specific terms or phrases.

    Args:
        query: The keyword or phrase to search for.
        kb_ids: List of knowledge base IDs to search across.
        top_k: Maximum number of results to return.
    """
    from deerflow.stores import KnowledgeBaseStore

    store = get_store("kb")
    if not isinstance(store, KnowledgeBaseStore):
        return "Knowledge base store not available."

    import asyncio
    import concurrent.futures

    def _run():
        return asyncio.run(store.keyword_search(kb_ids, query, top_k))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        results = asyncio.run(store.keyword_search(kb_ids, query, top_k))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            results = pool.submit(_run).result()

    if not results:
        return f"No results found for '{query}'."

    lines = []
    for r in results:
        lines.append(f"**{r['filename']}** (score: {r.get('score', 0):.0f})")
        lines.append(r.get("snippet", "")[:500])
        lines.append("")
    return "\n".join(lines)
