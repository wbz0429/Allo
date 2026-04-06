"""Knowledge base read tool — read a document's full markdown content."""

from langchain.tools import tool

from deerflow.context import get_user_context
from deerflow.store_registry import get_store


@tool("knowledge_base_read", parse_docstring=True)
def knowledge_base_read_tool(filename: str) -> str:
    """Read a document's full markdown content by filename.

    Always available (no index needed). Use when you know which file to read.
    Automatically searches across all available knowledge bases.

    Args:
        filename: The document filename to read.
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

    async def _find_and_read():
        kbs = await store.list_knowledge_bases(ctx.org_id)
        for kb in kbs:
            if filename in kb.get("documents", []):
                content = await store.read_document(kb["id"], filename)
                if content is not None:
                    return content
        return None

    def _run():
        return asyncio.run(_find_and_read())

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        content = asyncio.run(_find_and_read())
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            content = pool.submit(_run).result()

    if content is None:
        return f"Document '{filename}' not found in any knowledge base."
    return content
