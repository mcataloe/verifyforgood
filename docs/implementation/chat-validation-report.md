<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: validation-report
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# DU-CHAT-001 Validation Report

Status: Implementation review complete; executable local validation pending  
Last updated: 2026-09-05  
Branch: `chat/du-chat-001-local-assistant`  
Related Delivery Unit: `DU-CHAT-001 — Local Conversational Assistant MVP`

## Repository-Side Validation Completed

- Current branch remains based on `main` and contains only the bounded Chat implementation, related tests, additive platform migration, local Chat configuration example, and Chat documentation.
- No Terraform or deployment resource changes are present.
- No Bedrock provider, Bedrock call path, MCP server/client, vector database, embeddings service, web-browsing capability, arbitrary SQL capability, arbitrary HTTP capability, shell execution, or write-capable model tool was added.
- The model-facing tool surface remains explicit and read-only.
- User and organization authority remain server-owned in the Chat API.
- The default orchestrator now applies `VerifyForGoodChatOutputPolicy`, which rewrites unsupported platform-owned trust/approval/fraud/safety/compliance/eligibility/donation/procurement/endorsement conclusions to an evidence-only boundary statement.
- Deterministic tests were added for provider timeout, provider unavailability, rate limiting, provider context limits, malformed responses, refusal, empty responses, tool policy/validation/timeout codes, and semantic retrieval failure.
- Python syntax compilation was performed on the newly authored policy/orchestrator/safety-test source equivalents before repository writes. This is a syntax check only, not an import/integration test.

## Executable Validation Attempted but Unavailable

The ChatGPT runtime used for this implementation does not have a VerifyForGood checkout mounted.

A direct clone attempt failed with:

```text
fatal: unable to access 'https://github.com/mcataloe/verifyforgood.git/': Could not resolve host: github.com
```

The runtime also does not provide `pnpm` or the `ollama` executable.

A direct HTTP probe to the standard local Ollama endpoint failed with connection refused:

```text
http://127.0.0.1:11434/api/tags
→ [Errno 111] Connection refused
```

GitHub reports no status checks or GitHub Actions workflow runs for the feature-branch head. The repository's documented CI posture is GitLab, and this environment did not execute GitLab jobs.

## Required Local Validation Before Closure

Run on a real local checkout of `chat/du-chat-001-local-assistant`:

```powershell
python -m verification.backend.shared.local_dev db-upgrade
python -m verification.backend.shared.local_dev db-current
python -m pytest -q tests/test_chat_conversations.py tests/test_chat_orchestrator.py tests/test_chat_tools.py tests/test_chat_api.py tests/test_chat_safety.py tests/test_alembic_customer_accounts.py
python -m pytest -q
```

From `frontend/`:

```powershell
pnpm --filter @charity-status/portal test
pnpm --filter @charity-status/portal typecheck
pnpm --filter @charity-status/portal lint
pnpm run format:check
pnpm run build
```

Then run the Ollama smoke test from `docs/implementation/chat-local-development.md` using a small installed model.

## Closure Rule

Do not mark `DU-CHAT-001` closed until the executable local validation and Ollama smoke test have been run and their results recorded. Weak local model answer quality is not a closure failure unless it exposes a structural provider/orchestration/schema/tooling defect.
