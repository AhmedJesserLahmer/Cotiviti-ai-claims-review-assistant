"""Generate -> parse -> validate -> (repair) loop for structured LLM output."""

from __future__ import annotations

from typing import Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from ai_platform.errors import OutputParseError, OutputValidationError
from ai_platform.prompts import REPAIR_INSTRUCTION
from ai_platform.providers.base import ChatMessage, LLMResponse
from ai_platform.validation.parsing import extract_json_object

M = TypeVar("M", bound=BaseModel)


class _Client(Protocol):
    async def generate(self, messages: list[ChatMessage], **kwargs) -> LLMResponse: ...


class RepairCounter(Protocol):
    def record_repair(self, error: str) -> None: ...


def _describe(exc: Exception) -> str:
    if isinstance(exc, ValidationError):
        parts = [
            f"{'.'.join(str(p) for p in err['loc']) or 'root'}: {err['msg']}" for err in exc.errors()[:5]
        ]
        return "schema validation failed (" + "; ".join(parts) + ")"
    return str(exc)


async def generate_structured(
    client: _Client,
    messages: list[ChatMessage],
    schema: type[M],
    *,
    max_repairs: int = 1,
    schema_hint: str = "",
    recorder=None,
    counter: RepairCounter | None = None,
    **generate_kwargs,
) -> M:
    """Return a validated ``schema`` instance or raise ``OutputValidationError``.

    On invalid output the model is shown its own reply plus the validation error and
    asked to correct it, at most ``max_repairs`` times. Provider failures
    (``AllProvidersFailedError``) are not caught here; they propagate to the caller.
    """
    conversation = list(messages)
    last_error: Exception | None = None

    for attempt in range(max_repairs + 1):
        response = await client.generate(conversation, recorder=recorder, **generate_kwargs)
        try:
            return schema.model_validate(extract_json_object(response.text))
        except (OutputParseError, ValidationError) as exc:
            last_error = exc
            if attempt == max_repairs:
                break
            description = _describe(exc)
            if counter is not None:
                counter.record_repair(description)
            instruction = REPAIR_INSTRUCTION.format(error=description)
            if schema_hint:
                instruction += f"\nExpected shape: {schema_hint}"
            conversation += [ChatMessage.assistant(response.text[:2000]), ChatMessage.user(instruction)]

    raise OutputValidationError(f"model output invalid after {max_repairs} repair(s): {_describe(last_error)}")
