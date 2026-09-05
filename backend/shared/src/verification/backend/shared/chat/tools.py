from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Callable, Mapping

from verification.backend.shared.organization_verification.nonprofit_service import (
    TenantNonprofitContext,
)
from verification.backend.shared.organization_verification.verification_service import (
    OrganizationVerificationInput,
)

from .contracts import (
    ChatExecutionContext,
    ChatToolDefinition,
    ChatToolExecutionResult,
    ChatToolRequest,
)


class ChatToolError(RuntimeError):
    code = "tool_error"


class ChatToolPolicyError(ChatToolError):
    code = "tool_not_allowed"


class ChatToolValidationError(ChatToolError):
    code = "invalid_tool_arguments"


class ChatToolExecutionError(ChatToolError):
    code = "tool_execution_failed"


class ChatToolPolicy:
    def __init__(self, allowed_names: set[str] | frozenset[str]) -> None:
        self._allowed_names = frozenset(str(name).strip() for name in allowed_names if str(name).strip())

    def authorize(self, request: ChatToolRequest) -> None:
        if request.name not in self._allowed_names:
            raise ChatToolPolicyError(f"Chat tool is not allowlisted: {request.name}")


ToolHandler = Callable[[Mapping[str, Any], ChatExecutionContext], Any]


class ChatToolRegistry:
    """Explicit read-only application tool registry with server-owned tenant context."""

    def __init__(
        self,
        *,
        nonprofit_service: Any | None = None,
        usage_service: Any | None = None,
        subscription_service: Any | None = None,
        settings_service: Any | None = None,
    ) -> None:
        self._definitions: dict[str, ChatToolDefinition] = {}
        self._handlers: dict[str, ToolHandler] = {}

        if nonprofit_service is not None:
            self._register_nonprofit_tools(nonprofit_service)
        if usage_service is not None:
            self._register(
                ChatToolDefinition(
                    name="chat_get_usage_summary",
                    description="Read the active organization's current monthly usage counters.",
                    input_schema=_object_schema({}),
                ),
                lambda arguments, context: _usage_summary(usage_service, context),
            )
        if subscription_service is not None:
            self._register(
                ChatToolDefinition(
                    name="chat_get_subscription_summary",
                    description="Read the active organization's current subscription summary.",
                    input_schema=_object_schema({}),
                ),
                lambda arguments, context: _subscription_summary(subscription_service, context),
            )
        if settings_service is not None:
            self._register(
                ChatToolDefinition(
                    name="chat_get_organization_settings",
                    description="Read the active organization's current profile, integration, and billing settings.",
                    input_schema=_object_schema({}),
                ),
                lambda arguments, context: _organization_settings(settings_service, context),
            )

        self._policy = ChatToolPolicy(set(self._definitions))

    def definitions(self, context: ChatExecutionContext) -> tuple[ChatToolDefinition, ...]:
        del context
        return tuple(self._definitions[name] for name in sorted(self._definitions))

    def execute(
        self,
        request: ChatToolRequest,
        context: ChatExecutionContext,
    ) -> ChatToolExecutionResult:
        self._policy.authorize(request)
        definition = self._definitions[request.name]
        arguments = _validate_object_arguments(request.arguments, definition.input_schema)
        handler = self._handlers[request.name]
        try:
            data = handler(arguments, context)
        except ChatToolError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise ChatToolExecutionError(f"Chat tool failed: {request.name}") from exc

        payload = _normalize_tool_payload(request.name, data)
        return ChatToolExecutionResult(
            request_id=request.request_id,
            name=request.name,
            content=json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_json_default),
            metadata={
                "retrieval_mode": "structured",
                "tool": request.name,
                "status": payload["status"],
            },
        )

    def _register_nonprofit_tools(self, service: Any) -> None:
        self._register(
            ChatToolDefinition(
                name="chat_search_nonprofits",
                description="Search U.S. nonprofits by name using the existing tenant-scoped nonprofit service.",
                input_schema=_object_schema(
                    {
                        "query": {"type": "string", "minLength": 1, "maxLength": 200},
                        "state": {"type": "string", "minLength": 2, "maxLength": 2},
                        "active_only": {"type": "boolean"},
                        "limit": {"type": "integer", "minimum": 1, "maximum": 10},
                    },
                    required=("query",),
                ),
            ),
            lambda arguments, context: _search_nonprofits(service, arguments, context),
        )
        self._register(
            ChatToolDefinition(
                name="chat_get_nonprofit_profile",
                description="Read an evidence-focused nonprofit profile by EIN from the existing tenant-scoped nonprofit service.",
                input_schema=_object_schema(
                    {
                        "ein": {"type": "string", "minLength": 9, "maxLength": 12},
                        "name": {"type": "string", "minLength": 1, "maxLength": 255},
                    },
                    required=("ein",),
                ),
            ),
            lambda arguments, context: _nonprofit_profile(service, arguments, context),
        )
        self._register(
            ChatToolDefinition(
                name="chat_get_nonprofit_filings",
                description="Read filing summaries for a nonprofit EIN from the existing tenant-scoped nonprofit service.",
                input_schema=_object_schema(
                    {"ein": {"type": "string", "minLength": 9, "maxLength": 12}},
                    required=("ein",),
                ),
            ),
            lambda arguments, context: _nonprofit_filings(service, arguments, context),
        )

    def _register(self, definition: ChatToolDefinition, handler: ToolHandler) -> None:
        if not definition.name.startswith("chat_"):
            raise ValueError("Model-accessible tools must use the chat_ capability prefix")
        if definition.name in self._definitions:
            raise ValueError(f"Duplicate chat tool: {definition.name}")
        self._definitions[definition.name] = definition
        self._handlers[definition.name] = handler


def _tenant_context(context: ChatExecutionContext) -> TenantNonprofitContext:
    return TenantNonprofitContext(
        organization_id=str(context.organization_id),
        authenticated_subject=f"user:{context.user_id}",
        authenticated_user_id=str(context.user_id),
        auth_method="portal_chat",
        credential_id=None,
        metadata={"source": "chat"},
    )


def _search_nonprofits(service: Any, arguments: Mapping[str, Any], context: ChatExecutionContext) -> dict[str, Any]:
    status_code, payload = service.search_nonprofits(
        tenant_context=_tenant_context(context),
        name_query=str(arguments["query"]),
        limit=int(arguments.get("limit", 5)),
        state=_optional_string(arguments.get("state")),
        active_only=bool(arguments.get("active_only", False)),
    )
    return _status_payload(status_code, payload)


def _nonprofit_profile(service: Any, arguments: Mapping[str, Any], context: ChatExecutionContext) -> dict[str, Any]:
    status_code, payload = service.lookup_nonprofit(
        tenant_context=_tenant_context(context),
        verification_input=OrganizationVerificationInput(
            ein=str(arguments["ein"]),
            provided_name=_optional_string(arguments.get("name")),
        ),
    )
    if status_code != 200:
        return _status_payload(status_code, payload)

    # Do not hand legacy approve/deny/final recommendation fields to the model as
    # platform authority. The evidence/review layers remain available.
    safe_keys = (
        "organization",
        "verification",
        "name_verification",
        "filing_summary",
        "review",
        "evidence",
        "enrichment",
        "integration_evaluation",
        "score_explanation",
        "scores",
        "model_version",
        "source_data_versions",
        "queryExecutionId",
    )
    safe_payload = {key: payload[key] for key in safe_keys if key in payload}
    return {"status_code": 200, "data": safe_payload}


def _nonprofit_filings(service: Any, arguments: Mapping[str, Any], context: ChatExecutionContext) -> dict[str, Any]:
    status_code, payload = service.get_filings(
        tenant_context=_tenant_context(context),
        ein=str(arguments["ein"]),
    )
    return _status_payload(status_code, payload)


def _usage_summary(service: Any, context: ChatExecutionContext) -> dict[str, Any]:
    records = service.get_monthly_usage(organization_id=str(context.organization_id))
    return {"status_code": 200, "data": [_to_plain(record) for record in records]}


def _subscription_summary(service: Any, context: ChatExecutionContext) -> dict[str, Any]:
    response = service.get_subscription_for_organization(str(context.organization_id))
    return {"status_code": 200, "data": _to_plain(response.to_dict())}


def _organization_settings(service: Any, context: ChatExecutionContext) -> dict[str, Any]:
    organization_id = str(context.organization_id)
    document = service.get_settings(
        organization_id=organization_id,
        workspace_id=organization_id,
        account_id=organization_id,
    )
    return {"status_code": 200, "data": _to_plain(document.to_dict())}


def _normalize_tool_payload(tool_name: str, value: Any) -> dict[str, Any]:
    plain = _to_plain(value)
    status_code = 200
    data = plain
    if isinstance(plain, dict) and "status_code" in plain:
        try:
            status_code = int(plain.get("status_code", 200))
        except (TypeError, ValueError):
            status_code = 500
        data = plain.get("data")
    status = "ok" if 200 <= status_code < 300 else ("not_found" if status_code == 404 else "unavailable")
    return {
        "retrieval_mode": "structured",
        "tool": tool_name,
        "status": status,
        "status_code": status_code,
        "data": data,
    }


def _status_payload(status_code: int, payload: Any) -> dict[str, Any]:
    return {"status_code": int(status_code), "data": _to_plain(payload)}


def _object_schema(
    properties: Mapping[str, Mapping[str, Any]],
    *,
    required: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {key: dict(value) for key, value in properties.items()},
        "required": list(required),
        "additionalProperties": False,
    }


def _validate_object_arguments(arguments: Any, schema: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(arguments, Mapping):
        raise ChatToolValidationError("Tool arguments must be an object")
    properties = schema.get("properties") or {}
    if not isinstance(properties, Mapping):
        raise ChatToolValidationError("Tool schema is invalid")
    required = set(schema.get("required") or [])
    unknown = set(arguments) - set(properties)
    if unknown and schema.get("additionalProperties") is False:
        raise ChatToolValidationError(f"Unknown tool arguments: {', '.join(sorted(unknown))}")
    missing = required - set(arguments)
    if missing:
        raise ChatToolValidationError(f"Missing required tool arguments: {', '.join(sorted(missing))}")

    validated: dict[str, Any] = {}
    for key, value in arguments.items():
        rule = properties.get(key)
        if not isinstance(rule, Mapping):
            continue
        expected = rule.get("type")
        if expected == "string":
            if not isinstance(value, str):
                raise ChatToolValidationError(f"{key} must be a string")
            length = len(value)
            if "minLength" in rule and length < int(rule["minLength"]):
                raise ChatToolValidationError(f"{key} is too short")
            if "maxLength" in rule and length > int(rule["maxLength"]):
                raise ChatToolValidationError(f"{key} is too long")
        elif expected == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                raise ChatToolValidationError(f"{key} must be an integer")
            if "minimum" in rule and value < int(rule["minimum"]):
                raise ChatToolValidationError(f"{key} is below the minimum")
            if "maximum" in rule and value > int(rule["maximum"]):
                raise ChatToolValidationError(f"{key} is above the maximum")
        elif expected == "boolean":
            if not isinstance(value, bool):
                raise ChatToolValidationError(f"{key} must be a boolean")
        validated[key] = value
    return validated


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return _to_plain(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_plain(item) for item in value]
    return value


def _json_default(value: Any) -> Any:
    plain = _to_plain(value)
    if plain is value:
        return str(value)
    return plain


def _optional_string(value: Any) -> str | None:
    normalized = str(value or "").strip()
    return normalized or None
