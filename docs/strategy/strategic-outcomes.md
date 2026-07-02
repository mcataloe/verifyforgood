<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: strategic-outcome-registry
  authority: draft
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Strategic Outcomes

Status: Draft pending project-owner ratification  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Desired observable project changes after ratification  
Related Initiatives: `INIT-001` through `INIT-009`

Strategic Outcomes describe conditions the project seeks to create. They are not implementation phases, feature lists, or claims that the condition already exists.

## SO-001 — Source Evidence Is Inspectable

- **Desired change:** Material nonprofit information can be traced to its source, source identity, retrieval time, reporting period, normalized value, and relevant limitations.
- **Beneficiaries:** Customers, reviewers, developers, auditors, and operators.
- **Success signals:** Evidence views identify sources and timestamps; material derived outputs link to their basis; raw and normalized evidence remain distinguishable.
- **Evidence:** API contracts, evidence payloads, source views, tests, and user workflows.
- **Constraints:** Source licenses, availability, freshness, privacy, and technical feasibility.
- **Related Initiatives:** `INIT-002`, `INIT-003`, `INIT-005`.
- **Status:** Draft.

## SO-002 — Customers Control Decision Semantics

- **Desired change:** Customers define or select the rules that determine verified, eligible, approved, denied, manual-review, and insufficient-data outcomes for their workflows.
- **Beneficiaries:** Customer organizations and authorized users.
- **Success signals:** Decision authority is explicit; policies are customer-scoped; outcomes identify the applied policy; platform outputs are not misrepresented as universal determinations.
- **Evidence:** Decision-authority documentation, policy contracts, authorization tests, API responses, and customer workflows.
- **Constraints:** Backward compatibility, legal/user-trust risk, authorization, and auditability.
- **Related Initiatives:** `INIT-001`, `INIT-004`, `INIT-005`.
- **Status:** Draft; governing customer-authority principle approved.

## SO-003 — Policy Outcomes Are Reproducible

- **Desired change:** A policy result can be reproduced from the customer context, policy identity/version, evidence context, derived-signal versions, matched rules, and evaluation time.
- **Beneficiaries:** Customers, support, auditors, operators, and developers.
- **Success signals:** Stable policy IDs/versions; matched-rule evidence; immutable or historically recoverable evaluations; documented precedence.
- **Evidence:** Policy models, persistence records, audit payloads, tests, and support workflows.
- **Constraints:** Data retention, schema compatibility, policy versioning, and customer privacy.
- **Related Initiatives:** `INIT-001`, `INIT-002`, `INIT-004`.
- **Status:** Draft; partially implemented without full customer policy versioning.

## SO-004 — Facts, Signals, and Outcomes Stay Distinct

- **Desired change:** Source facts, normalized facts, evidence states, derived scores, baseline evaluations, policy results, and customer determinations remain semantically separate.
- **Beneficiaries:** All API, portal, and documentation users.
- **Success signals:** Contracts and UI identify output class; no universal meaning is inferred from compatibility labels; public copy matches authority.
- **Evidence:** Schemas, API payloads, UI labels, docs, tests, and decision-authority reviews.
- **Constraints:** Existing API compatibility and stored payloads.
- **Related Initiatives:** `INIT-001`, `INIT-002`, `INIT-005`, `INIT-008`.
- **Status:** Draft; material current drift recorded.

## SO-005 — Uncertainty Remains Honest

- **Desired change:** Not found, unknown, unavailable, stale, conflicting, failed, not offered, disabled, not required, and adverse evidence remain distinct throughout the system.
- **Beneficiaries:** Customers, reviewers, developers, and operators.
- **Success signals:** Failure and unknown states are explicit; missing evidence is not silently treated as negative; conflict and freshness are visible.
- **Evidence:** Models, API contracts, tests, runbooks, and user workflows.
- **Constraints:** Upstream source behavior and compatibility.
- **Related Initiatives:** `INIT-001`, `INIT-002`, `INIT-003`, `INIT-005`.
- **Status:** Draft; partially implemented.

## SO-006 — Regulatory Data Is Fresh and Traceable

- **Desired change:** Ingestion and refresh workflows preserve evidence, detect source changes, report run state, and avoid silently presenting stale information as current.
- **Beneficiaries:** Customers, operators, and downstream integrations.
- **Success signals:** Observable runs; retained source metadata; explicit freshness; repeatable refresh; error/partial-success reporting.
- **Evidence:** Ingest architecture, runbooks, manifests, run records, tests, and materialized profiles.
- **Constraints:** Source publication schedules, compute cost, availability, and retention.
- **Related Initiatives:** `INIT-002`, `INIT-003`, `INIT-007`.
- **Status:** Draft; partially implemented.

## SO-007 — Product Surfaces Use Shared Contracts

- **Desired change:** API, portal, marketing, and documentation surfaces use consistent, evidence-based terminology and do not independently invent verification or eligibility semantics.
- **Beneficiaries:** Customers, developers, sales/support, and maintainers.
- **Success signals:** Shared contract terminology; documented compatibility; product claims match implementation; drift checks cover public wording.
- **Evidence:** API docs, frontend copy, shared types, tests, and customer documentation.
- **Constraints:** Existing public contracts and staged rollout.
- **Related Initiatives:** `INIT-001`, `INIT-005`, `INIT-008`, `INIT-009`.
- **Status:** Draft; material drift remains.

## SO-008 — Technical Boundaries Remain Evolvable

- **Desired change:** Reusable deterministic logic, customer-private configuration, runtime orchestration, and deployment assets have explicit dependency and ownership boundaries.
- **Beneficiaries:** Maintainers, contributors, operators, and downstream adopters.
- **Success signals:** Enforced dependency direction; explicit public/private boundaries; infrastructure does not own business logic; migrations preserve compatibility.
- **Evidence:** Architecture docs, split tests, package structure, import checks, and ADRs.
- **Constraints:** Existing runtime paths, deployed resources, and contract stability.
- **Related Initiatives:** `INIT-001`, `INIT-003`, `INIT-004`, `INIT-006`, `INIT-007`, `INIT-009`.
- **Status:** Draft; transitional implementation.

## Ratification Rule

Do not mark an outcome achieved without explicit evidence and approval. Numeric targets require an approved source; do not invent them.
