<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: domain-map
  authority: draft
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Domain Map

Status: Draft pending project-owner ratification  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Persistent responsibility boundaries after ratification

Domains persist across roadmap cycles and may be touched by several Initiatives. They are not temporary work packages and do not define Roadmap priority.

| Domain | Purpose and responsibilities | Boundaries | Primary sources / docs | Related Initiatives | Sensitivity | Status |
|---|---|---|---|---|---|---|
| Source Acquisition | Discover and retrieve source artifacts with source identity and retrieval metadata | Does not interpret customer eligibility | Source modules and Form 990 discovery | `INIT-002`, `INIT-003` | Source terms, freshness | Draft / partial |
| Regulatory Filing Ingestion | Download, parse, normalize, stage, and refresh IRS and filing data | Does not own customer policy | Form 990 modules and monthly ingest docs | `INIT-003`, `INIT-007` | Data durability, cost | Draft / active |
| Entity Resolution | Normalize identifiers and compare organization identity/name evidence | Does not declare legal identity beyond evidence | Normalization and verification services | `INIT-002`, `INIT-005` | Ambiguous matching | Draft / partial |
| Organization Verification Evidence | Assemble organization, filing, source, and supporting evidence | Evidence is not a universal determination | Verification service and evidence builder | `INIT-001`, `INIT-002`, `INIT-005` | High trust sensitivity | Draft / active |
| Evidence and Provenance | Preserve source, time, period, transformations, completeness, conflicts, and freshness | Does not own business outcome | Evidence modules and audit payloads | `INIT-001`, `INIT-002`, `INIT-003` | High trust/data sensitivity | Draft / partial |
| Scoring and Derived Signals | Produce deterministic explainable scores and factors | Scores are not customer decisions | Scoring and weighting profiles | `INIT-001`, `INIT-002` | High semantic sensitivity | Draft / drift recorded |
| Customer Decision Policy | Represent and execute rules customers select or define | Pure evaluator differs from customer-private policy data | Policy engine/config and Decision Authority | `INIT-001`, `INIT-004`, `INIT-007` | High contract/user-trust risk | Draft / partial |
| Customer Decision Audit | Preserve policy context, matched rules, evidence basis, evaluation time, and future final action | Does not change outcomes | Audit/evidence payloads and future history | `INIT-001`, `INIT-002`, `INIT-004` | Data retention/privacy | Draft / partial |
| Identity and Access | Authenticate and authorize organization-scoped actions | Does not own policy meaning | Auth modules and identity ADR | `INIT-004`, `INIT-005`, `INIT-006` | High security/identity risk | Draft / active |
| Customer Organizations | Manage accounts, workspaces, membership, settings, and scoped resources | Does not own reusable evaluator logic | Control-plane and settings services | `INIT-004`, `INIT-005`, `INIT-006` | Tenant isolation/privacy | Draft / active |
| API and Developer Platform | Provide stable routes, envelopes, credentials, usage contracts, and guidance | Does not invent Domain semantics | Routes, responses, entrypoints, docs | `INIT-001`, `INIT-005`, `INIT-008` | Public contract risk | Draft / active |
| Portal Experience | Present authenticated customer workflows | Uses shared contracts and authority | `frontend/portal` | `INIT-004`, `INIT-005`, `INIT-006` | Accessibility/user trust | Draft / active |
| Billing and Usage | Plans, entitlements, quotas, usage, hosted billing, and billing state | Money/pricing require approval | Billing modules, plan docs, ADR | `INIT-006`, `INIT-007` | High money/user-trust risk | Draft / reconcile |
| Administration and Operations | Admin control plane, diagnostics, support, and operational actions | Separate from customer-safe surfaces | Ops/control-plane and runbooks | `INIT-003`, `INIT-004`, `INIT-006`, `INIT-007` | Security/production risk | Draft / active |
| Public Marketing and Documentation | Public messaging, developer/customer docs, brand/support presentation | Must not overstate authority | Marketing/docs apps and customer README | `INIT-001`, `INIT-005`, `INIT-008`, `INIT-009` | High user-trust risk | Draft / active |
| Infrastructure and Deployment | Terraform, runtime composition, packaging, deployed resources, and orchestration | Should not own reusable business logic | Terraform, runtime, deployment docs | `INIT-003`, `INIT-006`, `INIT-007` | Security, cost, durability | Draft / transitional |

## Relationship Rules

- An Initiative may affect several Domains.
- A Domain may be affected by several Initiatives over time.
- Domain ownership does not imply all implementation lives in one package or repository.
- Architecture describes technical realization; it does not replace this responsibility map.
- Unknown owners remain explicit rather than assigned by inference.
