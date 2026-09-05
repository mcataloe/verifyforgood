from __future__ import annotations

from dataclasses import asdict, dataclass
import os
from typing import Any, Callable
from uuid import uuid4

from fastapi import APIRouter, Request
from fastapi.responses import Response

from verification.backend.shared.api import build_response_context, error_response, json_response
from verification.backend.shared.auth import AuthenticationError
from verification.backend.shared.chat import (
    ChatConversationOrchestrator,
    ChatConversationService,
    ChatExecutionContext,
    ChatMessageRole,
    ChatModelMessage,
    ChatModelResolver,
    ChatModelRole,
    ChatModelRouter,
    ChatModelSettings,
    ChatOrchestrationError,
    ChatProviderRegistry,
    ChatToolRegistry,
    ConversationNotFoundError,
    FakeChatLLMProvider,
    OllamaChatLLMProvider,
    SqlAlchemyChatConversationRepository,
)
from verification.backend.shared.customer_accounts import build_customer_accounts_session_factory
from verification.backend.shared.platform import resolve_postgres_sqlalchemy_url

from .transport import runtime_response_to_http


@dataclass(frozen=True)
class ChatApiServices:
    conversations: ChatConversationService
    orchestrator: ChatConversationOrchestrator
    auth_service: Any
    organization_context_service: Any


ChatApiServicesFactory = Callable[[], ChatApiServices]
_chat_api_services: ChatApiServices | None = None


def create_chat_router(services_factory: ChatApiServicesFactory | None = None) -> APIRouter:
    router = APIRouter(prefix="/v1/chat", tags=["chat"])
    get_services = services_factory or _get_chat_api_services

    @router.post("/conversations")
    async def create_conversation(request: Request) -> Response:
        try:
            services, context = _authorized_context(request, get_services())
            body = await _read_json_object(request)
            conversation = services.conversations.create_conversation(
                user_id=context.user_id,
                organization_id=context.organization_id,
                title=_optional_text(body.get("title")),
            )
            return _success(request, 201, {"conversation": _conversation_dict(conversation)})
        except Exception as exc:  # noqa: BLE001
            return _error_from_exception(request, exc)

    @router.get("/conversations")
    async def list_conversations(request: Request) -> Response:
        try:
            services, context = _authorized_context(request, get_services())
            conversations = services.conversations.list_conversations(
                user_id=context.user_id,
                organization_id=context.organization_id,
            )
            return _success(
                request,
                200,
                {"conversations": [_conversation_dict(item) for item in conversations]},
            )
        except Exception as exc:  # noqa: BLE001
            return _error_from_exception(request, exc)

    @router.get("/conversations/{conversation_id}")
    async def get_conversation(conversation_id: int, request: Request) -> Response:
        try:
            services, context = _authorized_context(request, get_services())
            conversation = services.conversations.get_conversation(
                conversation_id,
                user_id=context.user_id,
                organization_id=context.organization_id,
            )
            messages = services.conversations.list_messages(
                conversation_id,
                user_id=context.user_id,
                organization_id=context.organization_id,
            )
            return _success(
                request,
                200,
                {
                    "conversation": _conversation_dict(conversation),
                    "messages": [_message_dict(item) for item in messages],
                },
            )
        except Exception as exc:  # noqa: BLE001
            return _error_from_exception(request, exc)

    @router.post("/conversations/{conversation_id}/messages")
    async def send_message(conversation_id: int, request: Request) -> Response:
        try:
            services, context = _authorized_context(request, get_services())
            body = await _read_json_object(request)
            content = str(body.get("content") or "").strip()
            if not content:
                raise ValueError("content is required")

            services.conversations.get_conversation(
                conversation_id,
                user_id=context.user_id,
                organization_id=context.organization_id,
            )
            prior_messages = services.conversations.list_messages(
                conversation_id,
                user_id=context.user_id,
                organization_id=context.organization_id,
            )
            user_message = services.conversations.append_message(
                conversation_id,
                user_id=context.user_id,
                organization_id=context.organization_id,
                role=ChatMessageRole.USER,
                content=content,
            )
            orchestration = services.orchestrator.run(
                context=context,
                user_message=content,
                history=tuple(_model_message(item) for item in prior_messages),
            )
            assistant_message = services.conversations.append_message(
                conversation_id,
                user_id=context.user_id,
                organization_id=context.organization_id,
                role=ChatMessageRole.ASSISTANT,
                content=orchestration.content,
                metadata={
                    "route_tier": orchestration.route.tier.value,
                    "route_reason": orchestration.route.reason_code,
                    "retrieval_mode": orchestration.retrieval_route.mode.value,
                    "retrieval_reason": orchestration.retrieval_route.reason_code,
                    "provider": orchestration.resolved_model.provider,
                    "model": orchestration.resolved_model.model,
                    "tool_names": sorted({result.name for result in orchestration.tool_results}),
                },
            )
            return _success(
                request,
                200,
                {
                    "user_message": _message_dict(user_message),
                    "assistant_message": _message_dict(assistant_message),
                    "orchestration": {
                        "route_tier": orchestration.route.tier.value,
                        "route_reason": orchestration.route.reason_code,
                        "retrieval_mode": orchestration.retrieval_route.mode.value,
                        "retrieval_reason": orchestration.retrieval_route.reason_code,
                        "provider": orchestration.resolved_model.provider,
                        "model": orchestration.resolved_model.model,
                        "tool_names": sorted({result.name for result in orchestration.tool_results}),
                        "invocation_count": len(orchestration.diagnostics),
                    },
                },
            )
        except Exception as exc:  # noqa: BLE001
            return _error_from_exception(request, exc)

    return router


def _get_chat_api_services() -> ChatApiServices:
    global _chat_api_services
    if _chat_api_services is None:
        from . import runtime

        session_factory = build_customer_accounts_session_factory(
            resolve_postgres_sqlalchemy_url(os.environ)
        )
        conversations = ChatConversationService(
            SqlAlchemyChatConversationRepository(session_factory)
        )
        settings = ChatModelSettings.from_env(os.environ)
        providers = ChatProviderRegistry(
            [
                FakeChatLLMProvider(),
                OllamaChatLLMProvider(
                    base_url=os.environ.get("CHAT_OLLAMA_BASE_URL", "http://127.0.0.1:11434"),
                    timeout_seconds=float(os.environ.get("CHAT_OLLAMA_TIMEOUT_SECONDS", "30")),
                ),
            ]
        )
        tools = ChatToolRegistry(
            nonprofit_service=runtime._get_nonprofit_service(),
            usage_service=runtime._get_portal_usage_service(),
            subscription_service=runtime._get_portal_subscription_service(),
            settings_service=runtime._get_organization_settings_service(),
        )
        orchestrator = ChatConversationOrchestrator(
            providers=providers,
            router=ChatModelRouter(),
            resolver=ChatModelResolver(settings),
            tool_executor=tools,
        )
        _chat_api_services = ChatApiServices(
            conversations=conversations,
            orchestrator=orchestrator,
            auth_service=runtime._get_portal_auth_service(),
            organization_context_service=runtime._get_portal_organization_context_service(),
        )
    return _chat_api_services


def _authorized_context(
    request: Request,
    services: ChatApiServices,
) -> tuple[ChatApiServices, ChatExecutionContext]:
    authorization = str(request.headers.get("authorization") or "").strip()
    if not authorization:
        token = str(request.cookies.get(os.environ.get("PORTAL_AUTH_COOKIE_NAME", "verifyforgood_portal_session")) or "").strip()
        if token:
            authorization = f"Bearer {token}"
    user = services.auth_service.get_current_user(authorization)
    organization = services.organization_context_service.resolve_for_user(user_id=str(user.user_id))
    if organization is None:
        raise ChatApiOrganizationContextError("Active organization context is required for Chat")
    return services, ChatExecutionContext(
        user_id=_positive_int(user.user_id, "user_id"),
        organization_id=_positive_int(organization.organization_id, "organization_id"),
        request_id=str(request.headers.get("x-request-id") or uuid4()),
    )


class ChatApiOrganizationContextError(RuntimeError):
    pass


async def _read_json_object(request: Request) -> dict[str, Any]:
    try:
        payload = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise ValueError("Request body must be valid JSON") from exc
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError("Request body must be a JSON object")
    return payload


def _success(request: Request, status_code: int, data: dict[str, Any]) -> Response:
    response_context = build_response_context(_response_event(request))
    return runtime_response_to_http(
        json_response(status_code, data, response_context=response_context)
    )


def _error(request: Request, status_code: int, message: str, code: str) -> Response:
    response_context = build_response_context(_response_event(request))
    return runtime_response_to_http(
        error_response(
            status_code,
            message,
            response_context=response_context,
            code=code,
        )
    )


def _error_from_exception(request: Request, exc: Exception) -> Response:
    if isinstance(exc, AuthenticationError):
        return _error(request, 401, "Authentication is required", "unauthorized")
    if isinstance(exc, ConversationNotFoundError):
        return _error(request, 404, "Conversation not found", "not_found")
    if isinstance(exc, ChatApiOrganizationContextError):
        return _error(request, 409, str(exc), "organization_context_required")
    if isinstance(exc, ChatOrchestrationError):
        status_code = 400 if exc.code in {"invalid_input", "input_too_large", "invalid_tool_arguments", "tool_not_allowed"} else 503
        return _error(request, status_code, str(exc), exc.code)
    if isinstance(exc, (ValueError, TypeError)):
        return _error(request, 400, str(exc), "bad_request")
    return _error(request, 500, "Chat request failed", "chat_internal_error")


def _response_event(request: Request) -> dict[str, Any]:
    return {
        "headers": {key: value for key, value in request.headers.items()},
        "requestContext": {
            "requestId": str(request.headers.get("x-request-id") or uuid4()),
        },
    }


def _conversation_dict(conversation: Any) -> dict[str, Any]:
    return asdict(conversation)


def _message_dict(message: Any) -> dict[str, Any]:
    data = asdict(message)
    role = data.get("role")
    data["role"] = getattr(role, "value", role)
    return data


def _model_message(message: Any) -> ChatModelMessage:
    role = ChatModelRole.USER if message.role is ChatMessageRole.USER else ChatModelRole.ASSISTANT
    return ChatModelMessage(role=role, content=message.content)


def _optional_text(value: Any) -> str | None:
    normalized = " ".join(str(value or "").strip().split())
    return normalized or None


def _positive_int(value: Any, field_name: str) -> int:
    try:
        normalized = int(value)
    except (TypeError, ValueError) as exc:
        raise ChatApiOrganizationContextError(f"{field_name} is not compatible with Chat persistence") from exc
    if normalized <= 0:
        raise ChatApiOrganizationContextError(f"{field_name} is not compatible with Chat persistence")
    return normalized


__all__ = ["ChatApiServices", "create_chat_router"]
