"""Knowledge base semantic search tool — requires indexed documents."""

from langchain.tools import tool

from deerflow.store_registry import get_store


@tool("knowledge_base_search", parse_docstring=True)
def knowledge_base_search_tool(query: str, kb_ids: list[str], top_k: int = 5) -> str:
    """Semantic search across indexed knowledge bases.

    Only works on documents that have been indexed (embeddings generated).
    If no indexed documents are found, suggests using keyword_search or read instead.

    Args:
        query: The search query for semantic matching.
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
        return asyncio.run(store.semantic_search(kb_ids, query, top_k))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        results = asyncio.run(store.semantic_search(kb_ids, query, top_k))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            results = pool.submit(_run).result()

    if not results:
        return (
            f"No semantic search results for '{query}'. "
            "This may mean no documents have been indexed yet. "
            "Try using knowledge_base_keyword_search (no index needed) or knowledge_base_read instead."
        )

    lines = []
    for r in results:
        lines.append(f"**Score: {r.get('score', 0):.3f}** (doc: {r.get('doc_id', 'unknown')})")
        lines.append(r.get("content", "")[:500])
        lines.append("")
    return "\n".join(lines)
