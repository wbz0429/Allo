"""Knowledge base list tool — list all knowledge bases and their documents."""

from langchain.tools import tool
from langchain_core.runnables import ensure_config

from deerflow.context import get_user_context
from deerflow.store_registry import get_store


@tool("knowledge_base_list", parse_docstring=True)
def knowledge_base_list_tool() -> str:
    """List all available knowledge bases and their documents.

    Use this to see what knowledge bases and files are available.
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

    def _run():
        return asyncio.run(store.list_knowledge_bases(ctx.org_id))

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        kbs = asyncio.run(store.list_knowledge_bases(ctx.org_id))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            kbs = pool.submit(_run).result()

    if not kbs:
        return "No knowledge bases found."

    lines = []
    for kb in kbs:
        docs = kb.get("documents", [])
        desc = f" ({kb['description']})" if kb.get("description") else ""
        lines.append(f"**{kb['name']}**{desc}")
        if docs:
            for d in docs:
                lines.append(f"  - {d}")
        else:
            lines.append("  (empty)")
    return "\n".join(lines)
