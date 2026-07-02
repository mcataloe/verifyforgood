<!--
LEAP_DOC_METADATA:
  audience: maintainer, agent, contributor
  doc_type: documentation-inventory
  authority: supporting
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Documentation Inventory

Status: Active supporting record  
Owner / approver: Project owner  
Last reconciled: 2026-07-02 against `main` at `694d07e1315ce266b274d6ca5008ca7a2e6a5f60`  
Canonical owner of: Document classification and lifecycle evidence  
Related Initiatives: `INIT-009`

This inventory records the highest-value project documents inspected during the Brownfield Recon. It does not make a document canonical merely by listing it. Merged code, tests, schemas, and contracts remain the authority for implemented behavior.

## Classification Vocabulary

- **Canonical** — ratified owner of a specific truth.
- **Approved principle** — explicit project-owner decision that may govern Draft documents.
- **Draft** — proposed source truth awaiting ratification.
- **Supporting** — useful evidence that does not own strategic truth.
- **Provisional** — decision or status record not yet ratified.
- **Historical** — preserves implementation or planning history.
- **Stale** — contradicted by newer evidence.
- **Do not use** — must not be used as current source truth.
- **Needs reconciliation** — combines or conflicts with several truth types.

## Inventory

| Path | Title / purpose | Type | Authority | Lifecycle | Current truth claimed | Repo evidence / conflict | Proposed canonical owner | Path action | Initiative / Domain |
|---|---|---|---|---|---|---|---|---|---|
| `AGENTS.md` | Repository agent rules | Governance | Supporting | Active | Contributor workflow | Omits Charter and LEAP reading order | `docs/00_start_here.md` plus retained repo rules | Keep; annotate | `INIT-009` |
| `README.md` | Repository overview, API, architecture, operations, history | Mixed | Supporting | Active / overloaded | Many project truths | Mixes implementation, historical Phases, architecture, and product copy | Multiple canonical owners | Keep; add entry-point and authority notice | All |
| `CUSTOMER_README.md` | Customer API and product overview | Product documentation | Supporting | Active | Customer surface and rollout notes | Must distinguish evidence and policy results from customer determinations | Charter and Decision Authority | Keep; clarify | `INIT-001`, `INIT-005`, `INIT-006` |
| `CUSTOMER_README copy.md` | Duplicate customer guide | Product documentation | Do not use candidate | Stale / conflicting | Pricing and stronger product claims | Conflicts with `CUSTOMER_README.md` pricing posture and authority language | `CUSTOMER_README.md` | Keep; mark do not use | `INIT-005`, `INIT-006` |
| `TODO.md` | Deferred work register | Backlog | Supporting | Active | Deferred tasks | Not a strategy or roadmap owner | Initiative registry and Roadmap | Keep; add ownership notice | All |
| `PLAN.md` | Completed ingest implementation plan | Historical plan | Historical | Completed | One bounded ingest change | Uses Phase 1–3 as implementation steps | Build Unit history | Keep; classify | `INIT-003` |
| `docs/repo-target-architecture.md` | Repository split assessment | Architecture | Supporting / provisional | Active | Current and target repository boundaries | Broadly classifies policy and decision logic as public-core candidates | Architecture docs and future ADR | Keep; annotate unresolved policy boundary | `INIT-001`, `INIT-007` |
| `docs/repo-split-guide.md` | Split migration guidance | Architecture | Supporting | Active | Public/private/infra placement | Must remain compatible with current runtime paths | Architecture index | Keep | `INIT-007` |
| `docs/backend-stage1-readiness.md` | Backend split readiness | Architecture / readiness | Supporting | Active snapshot | Entrypoint and contract readiness | Path and headings are test-sensitive | Architecture index | Keep | `INIT-007` |
| `docs/form990-ingest-plan.md` | Form 990 plan, architecture, status, history | Mixed | Needs reconciliation | Mixed | Ingest design and work status | Combines several lifecycle roles | `INIT-003` delivery/build records and architecture | Keep; later reconcile | `INIT-003` |
| `docs/monthly-ingest-architecture.md` | Monthly ingest architecture | Architecture | Supporting | Active | Workflow contracts and design | Strong technical source; not strategy | Architecture index | Keep | `INIT-003` |
| `docs/monthly-ingest-runbook.md` | Monthly ingest operations | Runbook | Supporting | Active | Deployment and operations | Operational source, not architecture owner | Runbook itself, indexed | Keep | `INIT-003` |
| `docs/capability-naming-abstraction.md` | Capability naming compatibility | Architecture convention | Supporting | Active | Naming boundary | Linked by tests and contributor docs | Architecture index | Keep | `INIT-007` |
| `docs/contributor-naming-rules.md` | Contributor naming rules | Contributor guidance | Supporting | Active | Three naming layers | Contains local machine links requiring repair | Architecture index | Keep; repair links | `INIT-007`, `INIT-009` |
| `docs/infrastructure-naming-normalization.md` | Infrastructure naming rules | Architecture convention | Supporting | Active | Terraform and physical-name conventions | Headings and references are test-sensitive | Architecture index | Keep | `INIT-007` |
| `docs/private-platform-service-areas.md` | Private-platform service areas | Architecture | Supporting | Active | Persistent platform service areas | Must not be confused with Initiatives | Domain and Architecture indexes | Keep | `INIT-004`, `INIT-006`, `INIT-007` |
| `docs/architecture/ADR-billing-provider.md` | Billing provider decision | ADR | Provisional | Active | Stripe provider direction | Ratification status not explicit | Architecture index / ADR | Keep; index | `INIT-006` |
| `docs/architecture/ADR-identity-datastore.md` | Identity datastore decision | ADR | Provisional | Active | Identity persistence direction | Ratification status not explicit | Architecture index / ADR | Keep; index | `INIT-004` |
| `docs/implementation/portal-identity-membership-plan.md` | Identity and membership plan | Implementation plan | Supporting | Mixed | Intended implementation | Must be reconciled with code and status record | `INIT-004` delivery/build records | Keep | `INIT-004` |
| `docs/implementation/portal-identity-membership-status.md` | Identity and membership status | Status | Needs reconciliation | Conflicting | Claims implementation status | Contains unrelated customer-support status wording | Repo reality and Initiative registry | Keep; flag/correct | `INIT-004` |
| `docs/implementation/billing-subscription-plan.md` | Billing implementation plan | Implementation plan | Supporting | Active / deferred items | Billing design and unresolved decisions | Retains production decisions after status says complete | `INIT-006` records and Architecture | Keep | `INIT-006` |
| `docs/implementation/billing-subscription-status.md` | Billing implementation status | Status | Needs reconciliation | Overbroad | Says billing track is complete | Conflicts with unresolved production decisions | Repo reality and Initiative registry | Keep; qualify | `INIT-006` |
| `docs/implementation/marketing-pricing-runtime-status.md` | Marketing pricing runtime status | Status | Supporting | Snapshot | Implemented pricing runtime behavior | Must not become pricing authority | Repo reality and billing docs | Keep | `INIT-006`, `INIT-008` |
| `frontend/README.md` | Frontend workspace architecture | Architecture / contributor guide | Supporting | Active | Workspace boundaries | Separate from repository-level governance docs | Architecture index | Keep | `INIT-005`, `INIT-008` |
| `frontend/marketing/README.md` | Marketing application guide | Contributor guide | Supporting | Active | Marketing runtime | Product surface, not Charter | Architecture index | Keep | `INIT-008` |
| `frontend/portal/README.md` | Portal application guide | Contributor guide | Supporting | Active | Portal runtime | Product surface, not strategy | Architecture index | Keep | `INIT-004`, `INIT-005` |
| `frontend/docs/README.md` | Documentation application guide | Contributor guide | Supporting | Active | Customer/developer docs runtime | Must remain distinct from repository `docs/` governance | Architecture index | Keep | `INIT-008` |
| `public-core/README.md` | Public-core extraction status | Architecture / packaging | Supporting | Transitional | Public-core boundary | Current runtime still uses legacy paths | Architecture index | Keep | `INIT-007` |
| `private-platform/README.md` | Private-platform extraction status | Architecture / packaging | Supporting | Transitional | Private-platform boundary | Customer policy storage boundary remains unresolved | Architecture index | Keep | `INIT-001`, `INIT-007` |
| `infra-deployment/README.md` | Deployment-boundary status | Architecture / packaging | Supporting | Transitional | Future deployment-only boundary | Infrastructure still contains runtime logic | Architecture index | Keep | `INIT-007` |
| `split-plan.json` | Machine-readable split plan | Architecture contract | Supporting | Active / incomplete | Migration candidate mapping | Does not distinguish pure evaluator from customer-private policy ownership | Future ADR and approved split update | Do not modify in `INIT-009` | `INIT-001`, `INIT-007` |

## Implementation Sources Inspected

The Recon also inspected current scoring, decision, policy, organization-integration settings, verification orchestration, and tests. Those sources establish implemented behavior but are not modified by `INIT-009`.

## Inventory Limits

This is the initial high-value inventory, not a claim that every Markdown file has been fully reconciled. Additional documents discovered during implementation must be added with evidence and an appropriate lifecycle status.
