import asyncio
import logging
from uuid import UUID

from langchain.chat_models import BaseChatModel
from langchain_core.callbacks.base import BaseCallbackHandler
from langchain_core.outputs import LLMResult

from deerflow.config import get_app_config, get_tracing_config, is_tracing_enabled
from deerflow.context import get_user_context
from deerflow.reflection import resolve_class
from deerflow.store_registry import get_store
from deerflow.stores import UsageRecordStore

logger = logging.getLogger(__name__)


class UsageTrackingCallbackHandler(BaseCallbackHandler):
    """Persist model token usage when runtime context and usage store are available."""

    def __init__(self, usage_store: UsageRecordStore) -> None:
        self._usage_store = usage_store

    @property
    def ignore_llm(self) -> bool:
        return False

    def on_llm_end(
        self,
        response: LLMResult,
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        **kwargs,
    ) -> None:
        del run_id, parent_run_id, tags, kwargs
        ctx = get_user_context()
        if ctx is None:
            return

        llm_output = response.llm_output or {}
        model_name = llm_output.get("model_name") if isinstance(llm_output, dict) else None
        token_usage = llm_output.get("token_usage") if isinstance(llm_output, dict) else None
        input_tokens = 0
        output_tokens = 0

        if isinstance(token_usage, dict):
            input_tokens = int(token_usage.get("prompt_tokens") or token_usage.get("input_tokens") or 0)
            output_tokens = int(token_usage.get("completion_tokens") or token_usage.get("output_tokens") or 0)

        if input_tokens == 0 and output_tokens == 0:
            generations = response.generations or []
            if generations and generations[0]:
                message = getattr(generations[0][0], "message", None)
                usage_metadata = getattr(message, "usage_metadata", None)
                if isinstance(usage_metadata, dict):
                    input_tokens = int(usage_metadata.get("input_tokens") or 0)
                    output_tokens = int(usage_metadata.get("output_tokens") or 0)
                if model_name is None:
                    response_metadata = getattr(message, "response_metadata", None)
                    if isinstance(response_metadata, dict):
                        model_name = response_metadata.get("model_name") or response_metadata.get("model")

        if input_tokens == 0 and output_tokens == 0:
            return

        try:
            asyncio.run(
                self._usage_store.record_llm_token(
                    user_id=ctx.user_id,
                    org_id=ctx.org_id,
                    model_name=str(model_name) if model_name else None,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                )
            )
        except RuntimeError:
            logger.warning("Failed to persist llm token usage due to active event loop", exc_info=True)
        except Exception:
            logger.warning("Failed to persist llm token usage", exc_info=True)


def create_chat_model(name: str | None = None, thinking_enabled: bool = False, **kwargs) -> BaseChatModel:
    """Create a chat model instance from the config.

    Args:
        name: The name of the model to create. If None, the first model in the config will be used.

    Returns:
        A chat model instance.
    """
    config = get_app_config()
    if name is None:
        name = config.models[0].name
    model_config = config.get_model_config(name)
    if model_config is None:
        raise ValueError(f"Model {name} not found in config") from None
    model_class = resolve_class(model_config.use, BaseChatModel)
    model_settings_from_config = model_config.model_dump(
        exclude_none=True,
        exclude={
            "use",
            "name",
            "display_name",
            "description",
            "supports_thinking",
            "supports_reasoning_effort",
            "when_thinking_enabled",
            "thinking",
            "supports_vision",
        },
    )
    # Compute effective when_thinking_enabled by merging in the `thinking` shortcut field.
    # The `thinking` shortcut is equivalent to setting when_thinking_enabled["thinking"].
    has_thinking_settings = (model_config.when_thinking_enabled is not None) or (model_config.thinking is not None)
    effective_wte: dict = dict(model_config.when_thinking_enabled) if model_config.when_thinking_enabled else {}
    if model_config.thinking is not None:
        merged_thinking = {**(effective_wte.get("thinking") or {}), **model_config.thinking}
        effective_wte = {**effective_wte, "thinking": merged_thinking}
    if thinking_enabled and has_thinking_settings:
        if effective_wte:
            model_settings_from_config.update(effective_wte)
    if not thinking_enabled and has_thinking_settings:
        if effective_wte.get("extra_body", {}).get("thinking", {}).get("type"):
            # OpenAI-compatible gateway: thinking is nested under extra_body
            kwargs.update({"extra_body": {"thinking": {"type": "disabled"}}})
            kwargs.update({"reasoning_effort": "minimal"})
        elif effective_wte.get("thinking", {}).get("type"):
            # Native langchain_anthropic: thinking is a direct constructor parameter
            kwargs.update({"thinking": {"type": "disabled"}})
    if not model_config.supports_reasoning_effort and "reasoning_effort" in kwargs:
        del kwargs["reasoning_effort"]

    model_instance = model_class(**kwargs, **model_settings_from_config)

    callbacks = list(model_instance.callbacks or [])
    usage_store = get_store("usage")
    if isinstance(usage_store, UsageRecordStore):
        callbacks.append(UsageTrackingCallbackHandler(usage_store))

    if is_tracing_enabled():
        try:
            from langchain_core.tracers.langchain import LangChainTracer

            tracing_config = get_tracing_config()
            tracer = LangChainTracer(
                project_name=tracing_config.project,
            )
            callbacks.append(tracer)
            logger.debug(f"LangSmith tracing attached to model '{name}' (project='{tracing_config.project}')")
        except Exception as e:
            logger.warning(f"Failed to attach LangSmith tracing to model '{name}': {e}")

    if callbacks:
        model_instance.callbacks = callbacks
    return model_instance
