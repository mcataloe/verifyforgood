<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: build-unit-registry
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# INIT-005 Build Units

Status: `DU-CHAT-001` implementation complete on feature branch; executable local validation pending  
Owner / approver: Project owner  
Last reconciled: 2026-09-05  
Initiative: `INIT-005 — Customer API and Portal Experience`

## DU-CHAT-001 — Local Conversational Assistant MVP

| Build Unit | Objective | Status | Primary evidence |
|---|---|---|---|
| `BU-CHAT-001` | Conversation persistence and user/organization ownership | Implemented | Chat SQLAlchemy models/repository/service, Alembic migration, isolation tests |
| `BU-CHAT-002` | Provider abstraction, application-owned model routing, orchestration | Implemented | Fake/Ollama providers, low/medium/high router/resolver, bounded orchestrator tests |
| `BU-CHAT-003` | Read-only model tool/retrieval surface | Implemented | `chat_` tool registry/policy, structured retrieval, disabled semantic retriever seam, tool tests |
| `BU-CHAT-004` | Authenticated customer Chat API | Implemented | Native FastAPI `/v1/chat/...` routes and API tests |
| `BU-CHAT-005` | Portal Chat UI and conversation history | Implemented | Portal Chat drawer/client/endpoints and org-switch stale-response tests |
| `BU-CHAT-006` | Safety, failure simulation, validation, documentation, cloud stop gate | Implemented; executable validation pending | Output-authority policy, deterministic failure tests, local-development/architecture docs, Ollama config example |

## Common Constraints

- Local Chat validation is pipeline validation, not model-quality validation.
- Local low/medium/high model tiers may all map to one small Ollama model.
- Model routing is application-owned; provider-specific model names remain configuration.
- The LLM may request a tool; the orchestrator decides whether it is valid, authorized, and executable.
- Model-accessible capabilities are explicit and read-only.
- User and organization scope are server-owned.
- No model-generated SQL, arbitrary HTTP, shell execution, arbitrary code execution, writes, MCP, web browsing, autonomous loops, or deployment-capable Bedrock integration are in scope.
- Structured application retrieval is preferred. Semantic/hybrid retrieval remains a seam until a real approved semantic retriever exists.
- Application decision-authority controls remain required in local and future cloud environments.

## Validation Boundary

The feature branch contains targeted tests for persistence, orchestration, tools, API behavior, frontend Chat behavior, output policy, and deterministic provider/retrieval/tool failure paths.

As of 2026-09-05, this ChatGPT execution environment has no mounted repository checkout, cannot resolve `github.com` for `git clone`, and does not provide `pnpm` or `ollama`. Therefore pytest, Alembic execution, frontend tests/typecheck/lint/build, browser smoke testing, and the real Ollama smoke test have not been executed from this environment.

Do not mark `DU-CHAT-001` closed until the current feature branch is checked out locally and the validation sequence in `docs/implementation/chat-local-development.md` is run and recorded.

## Cloud Stop Gate

A deployment-capable Bedrock Chat change is out of scope and must remain disabled until a separately approved change covers Bedrock Runtime, Bedrock Guardrails, IAM restrictions, model/tool allowlisting, cloud observability, cost controls, privacy/data handling, and production validation.
