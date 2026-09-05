<!--
LEAP_DOC_METADATA:
  audience: maintainer, contributor
  doc_type: implementation-guide
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# Local Chat Development

Status: Implemented; executable local validation pending on a checkout with PostgreSQL, frontend tooling, and Ollama  
Last reconciled: 2026-09-05  
Related Delivery Unit: `DU-CHAT-001 — Local Conversational Assistant MVP`

## Local Development Goal

Local Chat exists to validate the pipeline around the model, not production answer quality.

A small local model is expected. Local development should validate authentication, organization isolation, persistence, routing, retrieval/tool selection, schema validation, orchestration, output policy, diagnostics, and failure handling. Weak model prose or reasoning is not by itself a pipeline failure.

## Configuration

Use `backend/.env.local` for local settings. Do not commit real secrets.

Required when using Ollama:

```text
CHAT_PROVIDER=ollama
CHAT_LOCAL_MODEL=<small-installed-model>
```

Optional tier overrides:

```text
CHAT_MODEL_LOW=
CHAT_MODEL_MEDIUM=
CHAT_MODEL_HIGH=
```

If the tier-specific values are blank, all tiers resolve to `CHAT_LOCAL_MODEL`.

Ollama connection settings:

```text
CHAT_OLLAMA_BASE_URL=http://127.0.0.1:11434
CHAT_OLLAMA_TIMEOUT_SECONDS=30
```

For deterministic orchestration tests, use the fake provider in tests rather than depending on Ollama quality or availability.

## Suggested Local Startup

From the repository root after the normal backend/frontend setup:

```powershell
python -m verification.backend.shared.local_dev db-upgrade
python -m verification.backend.shared.local_dev db-current
python -m verification.backend.customer.api.entrypoint
```

From `frontend/` in a second terminal:

```powershell
pnpm run dev:portal
```

Confirm Ollama separately:

```powershell
ollama list
```

Choose a small installed model that fits the developer machine. The exact model name is configuration, not an architecture decision.

## Targeted Validation

Run targeted backend Chat tests first:

```powershell
python -m pytest -q tests/test_chat_conversations.py tests/test_chat_orchestrator.py tests/test_chat_tools.py tests/test_chat_api.py tests/test_chat_safety.py tests/test_alembic_customer_accounts.py
```

Then relevant auth/organization regression tests and, when practical, the broader backend suite:

```powershell
python -m pytest -q
```

Frontend checks from `frontend/`:

```powershell
pnpm --filter @charity-status/portal test
pnpm --filter @charity-status/portal typecheck
pnpm --filter @charity-status/portal lint
pnpm run format:check
pnpm run build
```

If workspace scripts differ in the active checkout, use the current `frontend/package.json`/package-local scripts rather than preserving an obsolete command.

## Ollama Smoke Test

The smoke test is successful when the provider/orchestrator contract works, even if the small model gives a weak answer.

1. Set `CHAT_PROVIDER=ollama` and `CHAT_LOCAL_MODEL` to a small installed model.
2. Start the customer API and portal.
3. Open Chat in the authenticated portal.
4. Send one direct/simple request and confirm a normalized assistant response.
5. Send one request that should use a read-only Chat tool and confirm the tool loop completes.
6. Confirm route tier, provider, model, and retrieval mode diagnostics are displayed/recorded.
7. Reload and confirm conversation persistence.
8. Switch organizations and confirm the previous organization's history is immediately cleared and not redisplayed.

Do not tune prompts to make the small local model appear production quality.

## Failure Validation

`FakeChatLLMProvider` accepts deterministic response/error steps. `tests/test_chat_safety.py` covers provider timeout, unavailability, rate limiting, context limits, malformed responses, refusal, empty responses, tool failure codes, and semantic retrieval failure.

These tests intentionally validate the orchestration contract without emulating Bedrock Guardrails.

## Known Local Boundaries

- No semantic/vector backend currently exists; structured retrieval is active and the semantic retriever seam is disabled by default.
- No Bedrock provider is implemented in this Delivery Unit.
- Bedrock Guardrails are not simulated locally as if they were equivalent to AWS behavior.
- The application decision-authority/output policy, tool allowlist, tenant authorization, and read-only enforcement are local and cloud requirements.

## Cloud Enablement Stop Gate

Do not enable deployment-capable Bedrock Chat until a separate approved change implements and validates Bedrock Runtime integration, Bedrock Guardrails, IAM restrictions, model/tool allowlisting, cloud observability, cost controls, and production privacy/data handling.
