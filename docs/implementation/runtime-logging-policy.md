# Runtime Logging Policy

Runtime logging now follows one environment-based policy across API, billing, and Form 990 runtimes.

- `LOG_LEVEL` wins when explicitly set.
- Otherwise `APP_ENV=prod` defaults to `INFO`.
- All other environments default to `DEBUG`.
- `LOG_STACK_TRACES` controls traceback emission explicitly.
- Without `LOG_STACK_TRACES`, production suppresses tracebacks and non-production includes them.

Operational logs must not emit raw credentials or payloads. The shared runtime logging helper redacts or omits:

- authorization headers
- tokens, secrets, passwords, API keys, webhook secrets
- database URLs with embedded credentials
- raw request and webhook bodies
- request and response header blobs

Allowed runtime log fields should stay high level:

- event names
- IDs
- statuses
- counts
- archive and file names
- timestamps
- route keys
- plan and billing state identifiers

When deeper diagnosis is required locally, prefer `LOG_LEVEL=DEBUG` and `LOG_STACK_TRACES=true` instead of adding new raw payload logging.
