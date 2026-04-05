"""Knowledge base read tool — read a document's full markdown content."""

from langchain.tools import tool

from deerflow.store_registry import get_store


@tool("knowledge_base_read", parse_docstring=True)
def knowledge_base_read_tool(kb_id: str, filename: str) -> str:
    """Read a document's full markdown content by filename.

    Always available (no index needed). Use when you know which file to read.

    Args:
        kb_id: The knowledge base ID.
        filename: The document filename to read.
    """
    from deerflow.stores import KnowledgeBaseStore

    store = get_store("kb")
    if not isinstance(store, KnowledgeBaseStore):
        return "Knowledge base store not available."

    import asyncio
    import concurrent.futures

    def _run():
        return asyncio.run(store.read_document(kb_id, filename))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        content = asyncio.run(store.read_document(kb_id, filename))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            content = pool.submit(_run).result()

    if content is None:
        return f"Document '{filename}' not found in this knowledge base."
    return content
