"""Knowledge base list tool — list documents in a knowledge base."""

from langchain.tools import tool

from deerflow.store_registry import get_store


@tool("knowledge_base_list", parse_docstring=True)
def knowledge_base_list_tool(kb_id: str) -> str:
    """List all documents in a knowledge base.

    Returns filename, size, and index status for each document.
    Use this first to see what's available before reading or searching.

    Args:
        kb_id: The knowledge base ID to list documents from.
    """
    from deerflow.stores import KnowledgeBaseStore

    store = get_store("kb")
    if not isinstance(store, KnowledgeBaseStore):
        return "Knowledge base store not available."

    import asyncio
    import concurrent.futures

    def _run():
        return asyncio.run(store.list_documents(kb_id))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        docs = asyncio.run(store.list_documents(kb_id))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            docs = pool.submit(_run).result()

    if not docs:
        return "No documents found in this knowledge base."

    lines = []
    for d in docs:
        size_kb = d.get("file_size", 0) / 1024
        lines.append(f"- {d['filename']} ({size_kb:.1f} KB, index: {d.get('index_status', 'none')})")
    return "\n".join(lines)
