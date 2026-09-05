<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: architecture-reference
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Chat Local-Cloud Parity Architecture

Status: Implemented locally; cloud provider enablement deferred  
Owner / approver: Project owner / Architecture owner  
Last reconciled: 2026-09-05  
Related Initiative: `INIT-005`  
Related Delivery Unit: `DU-CHAT-001 — Local Conversational Assistant MVP`

## Principle

Local Chat validation is pipeline validation, not model-quality validation.

Local-cloud parity is defined at the orchestration, authorization, policy, retrieval, persistence, routing, observability, provider-contract, and failure-handling layers. It is not defined as parity of model capability or final-answer quality.

## Runtime Shape

```text
Authenticated portal
        ↓
Customer Chat API
        ↓
server-owned user + active organization context
        ↓
ChatConversationOrchestrator
        ├── application-owned model router
        ├── retrieval router
        ├── read-only chat tool registry/policy
        ├── input/output policy
        ├── conversation persistence
        └── ChatLLMProvider
               ├── FakeChatLLMProvider
               └── OllamaChatLLMProvider
```

Future provider seam only:

```text
ChatLLMProvider
        └── Bedrock provider
              + Bedrock Guardrails
```

No deployment-capable Bedrock provider is part of `DU-CHAT-001`.

## Model Routing

Model routing is application-owned. The router chooses one of:

- `low`
- `medium`
- `high`

The router does not choose an Ollama or Bedrock model ID. Configuration resolves the selected tier to a provider-specific model.

For local development, all three tiers may map to the same small Ollama model:

```text
low    → small local model
medium → small local model
high   → small local model
```

The selected tier and routing reason are still recorded. Cloud deployment may later map the same tiers to materially different Bedrock models without changing orchestration semantics.

## Tool Boundary

The governing rule is:

> The LLM may request. The orchestrator decides.

The model does not directly execute SQL, HTTP, shell commands, arbitrary code, database clients, writes, deletes, billing changes, account changes, or credential operations.

Model-visible tools are explicit `chat_` read-only capabilities. User and organization scope are resolved server-side and are not model-authoritative tool arguments.

## Retrieval

Structured deterministic application retrieval is preferred when it can answer the request.

The retrieval router supports:

- structured retrieval
- semantic retrieval
- hybrid retrieval
- model-only handling when no retrieval capability exists

There is no vector/embedding implementation in the current repository. The semantic retriever is therefore a real interface but disabled by default. `DU-CHAT-001` does not add pgvector, a hosted vector database, embeddings infrastructure, or a new external retrieval service solely for architectural symmetry.

## Decision Authority and Output Policy

Chat must follow `docs/charter/decision-authority.md` and the accepted advisory-copilot doctrine.

The application output policy deterministically rewrites unsupported platform-owned conclusions such as independent trustworthiness, approval, fraud, safety, compliance, eligibility, donation, procurement, or endorsement determinations into an evidence-only boundary statement.

This policy is application-owned and remains required when a cloud model is introduced.

## Failure Handling

The fake provider and orchestration tests exercise deterministic failure paths including:

- provider timeout
- provider unavailable
- rate limiting
- context/input limits
- malformed provider response
- refusal
- empty response
- unknown or invalid tool requests
- tool timeout/error codes
- semantic retrieval failure

These are pipeline tests, not attempts to reproduce Bedrock internals.

## Persistence and Diagnostics

Conversation history is scoped to both authenticated user and active organization. Raw tool result payloads are not persisted as conversation messages.

Assistant message metadata records bounded orchestration diagnostics such as route tier/reason, retrieval mode/reason, provider, model, and tool names. Sensitive raw tool payloads should not be added to persistent diagnostics without a separate need and review.

## Cloud Stop Gate

Before deployment-capable Bedrock Chat is enabled, a separately approved change must cover at minimum:

- Bedrock Runtime provider implementation
- Bedrock Guardrails configuration and enforcement
- model/provider allowlisting
- IAM restrictions
- tool-use safety validation
- cloud observability
- cost controls
- production privacy/data review
- deployment validation

Application-level authorization, tool policy, input/output policy, tenant isolation, and decision-authority controls remain mandatory in addition to Bedrock Guardrails.
