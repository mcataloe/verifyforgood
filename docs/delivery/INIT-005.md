<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: delivery-unit-record
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# INIT-005 — Customer API and Portal Experience

Status: Active; `DU-CHAT-001` implementation complete with executable local validation pending  
Owner / approver: Project owner  
Last reconciled: 2026-09-05  
Strategic Outcomes: `SO-001`, `SO-002`, `SO-004`, `SO-005`, `SO-007`

## DU-CHAT-001 — Local Conversational Assistant MVP

- **Status:** Implementation complete on `chat/du-chat-001-local-assistant`; local executable validation and Ollama smoke test pending.
- **Outcome:** Authenticated portal users can use a persistent, organization-scoped conversational interface whose model provider, routing, retrieval, tools, authorization, policies, and diagnostics are structured for later cloud substitution.
- **Local validation objective:** Pipeline/orchestration correctness rather than production answer quality.
- **Provider posture:** Ollama locally, deterministic fake provider for tests, Bedrock deferred.
- **Model routing:** Application-owned `low | medium | high`; all local tiers may resolve to one small local model.
- **Retrieval posture:** Structured deterministic retrieval implemented; semantic/hybrid seam present but semantic retriever disabled because the repo has no approved vector/embedding backend.
- **Decision authority:** Advisory/evidence-only; customer owns determinations.
- **Tenant boundary:** User and active organization are resolved server-side; model/client input cannot elevate organization scope.
- **Tool boundary:** Explicit read-only `chat_` capabilities only; no model SQL/HTTP/shell/code execution/writes.
- **Cloud boundary:** No deployment-capable Bedrock implementation; Bedrock Guardrails required before future cloud enablement.

### Build Units

- `BU-CHAT-001 — Conversation Persistence and Ownership` — Implemented
- `BU-CHAT-002 — LLM Provider, Model Routing, and Conversation Orchestration` — Implemented
- `BU-CHAT-003 — Read-Only Chat Tool and Retrieval Surface` — Implemented
- `BU-CHAT-004 — Customer Chat API` — Implemented
- `BU-CHAT-005 — Portal Chat UI and History` — Implemented
- `BU-CHAT-006 — Safety, Failure Simulation, Validation, Documentation, and Cloud Stop Gate` — Implemented; executable validation pending

### Acceptance Criteria

Before closing `DU-CHAT-001`, local validation must demonstrate at minimum:

- platform/customer Alembic migration applies cleanly
- targeted Chat backend tests pass
- relevant auth/organization regression tests pass
- portal Chat tests/typecheck/lint/build pass or limitations are recorded
- one direct Ollama response round trip succeeds with a small installed model
- one Ollama tool-request round trip succeeds if the selected local model supports tool calling sufficiently
- conversation history persists for the same user/organization
- organization switching hides/clears prior organization history
- model/client organization identity cannot override server-owned scope
- unsupported platform-owned evaluative conclusions are rewritten by application output policy
- deterministic failure scenarios produce bounded errors

### Current Validation Limitation

The ChatGPT execution environment used for implementation does not have the repository checkout mounted. A direct `git clone` attempt fails because `github.com` cannot be resolved from the container. `pnpm` and `ollama` are also absent from that runtime. Therefore no pytest, Alembic, pnpm, browser, or real Ollama execution is claimed yet.

The committed tests and documentation define the validation sequence. `DU-CHAT-001` remains open until the local checkout run is completed and results are recorded.

### Rollback

The work is isolated on the feature branch and can be reverted by Build Unit commits. The Chat schema migration is additive and should be evaluated with the normal Alembic downgrade/rollback posture before any deployment.

### Future Work Outside This Delivery Unit

- production model-quality evaluation
- semantic/vector retrieval implementation if separately justified
- Bedrock provider implementation
- Bedrock Guardrails and IAM enforcement
- cloud model-tier mapping and cost policy
- production observability/privacy/cost validation
