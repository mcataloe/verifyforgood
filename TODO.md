# TODO

## TODO-ARCH-001

### Title

Complete post-cutover cleanup for the PostgreSQL-only platform persistence model.

### Rationale

The Phase 24A relational pivot assessment confirms that the current DynamoDB
footprint spans multiple relational domains:

- users
- organizations
- memberships
- invitations
- org-scoped subscriptions, usage, feature flags, API keys, and audit events
- organization settings
- control-plane accounts, billing events, OAuth clients, and account usage

The runtime cutover is now on PostgreSQL for the platform's relational domains,
but the repo still contains historical migration helpers, Dynamo-specific test
coverage, and documentation that assume the older mixed-mode posture.

The ECS-only runtime cutover is complete for the HTTP API, scheduled ingest,
and manual Form 990 task launches. Remaining follow-up here is cleanup of
historical compatibility language and obsolete mixed-mode tooling.

### Migration Triggers

- remove historical DynamoDB-only tests and compatibility docs that no longer
  reflect supported runtime behavior
- finish retiring obsolete migration-era scripts or move them under explicitly
  historical tooling boundaries
- complete the remaining nonprofit read-path simplification work

### Constraint

Keep service and repository interfaces stable while removing stale
mixed-mode assumptions from tooling, docs, and tests.

### Follow-On Sequence

1. remove stale DynamoDB runtime documentation and rollback guidance
2. retire or quarantine Dynamo-specific adapter tests that no longer reflect supported deployment paths
3. complete nonprofit read-model cleanup after the materialized cache retirement

## TODO-ARCH-002

### Title

Reconcile API Endpoints

### Rationale

Need to ensure that all API endpoints that are expected by the frontend repo are deployed in the infrastructure / data access layer.

### Migration Triggers

None

### Constraint

None

## TODO-ARCH-003

### Title

Link portal organizations to control-plane accounts and subscriptions for org-managed API keys.

### Rationale

Phase 19L introduces organization-managed API keys in the identity domain. Until portal organizations provision or map to control-plane accounts, these keys use a temporary compatibility model:

- `account_id = organization_id`
- `workspace_id = organization_id`
- `plan_id = free`

That is enough for initial authentication, but it does not inherit real billing, subscription, or entitlement state.

### Migration Triggers

- portal billing parity
- organization subscription-aware entitlements
- API key plan inheritance requirements
- multi-org account mapping

### Constraint

Keep the org-managed API-key repository/service interfaces stable so real control-plane linkage can replace the temporary compatibility mapping without changing frontend or handler contracts.

## TODO-ARCH-004

### Title

Reconcile portal subscription scaffolding with control-plane billing accounts and subscriptions.

### Rationale

Phase 19M introduces `PLAN` and `SUBSCRIPTION` entities in the portal identity domain so organization-linked subscription state can exist before full billing parity. The repo already has a mature control-plane billing model, so these portal records are scaffolding until a real linkage model is implemented.

### Migration Triggers

- portal billing UI parity
- Stripe-backed portal subscription changes
- entitlement inheritance from paid subscriptions
- organization to control-plane account mapping

### Constraint

Keep the portal `PlanRepository`, `SubscriptionRepository`, and `SubscriptionService` contracts stable so control-plane linkage can replace the scaffolded storage model without changing portal-facing callers.

## TODO-ARCH-005

### Title

SSO integration design details pending.

### Rationale

Phase 19P adds identity-provider seams and user provider metadata, but it does not define the full SAML/OIDC integration model yet.

Open design areas include:

- provider configuration storage
- tenant-to-provider mapping
- account linking and JIT provisioning rules
- assertion validation boundaries
- admin onboarding and certificate/metadata rotation

### Migration Triggers

- first SAML pilot
- first OIDC enterprise integration
- provider discovery and login initiation requirements

### Constraint

Keep the `IdentityProviderService` abstraction and user provider fields stable so future SSO support can plug in without breaking the existing local-password auth flow.

## TODO-ARCH-006

### Title

Define tenant-resolution support for non-portal machine clients on nonprofit query routes.

### Rationale

Phase 20A makes nonprofit query routes organization-aware and intentionally supports only:

- organization-managed API keys
- portal bearer sessions with current-organization headers

Generic control-plane API keys and OAuth client-credentials tokens remain unsupported until there is a stable way to resolve them to an organization membership or equivalent tenant scope.

### Migration Triggers

- tenant-scoped machine-to-machine access requirements
- partner or integration clients that need nonprofit query access
- organization-linked OAuth client design

### Constraint

Keep the new tenant nonprofit service contract stable so future non-portal machine-auth support can plug in by adding tenant resolution, not by changing nonprofit lookup callers.

## TODO-ARCH-007

### Title

Decide whether nonprofit source, compliance, and federal-awards routes need dedicated organization usage metrics.

### Rationale

Phase 20B adds dedicated usage counters for:

- nonprofit lookup requests
- nonprofit search requests
- nonprofit filing lookup requests

Other tenant-scoped nonprofit read routes still rely on broader request metering and do not yet have dedicated per-route usage categories.

### Migration Triggers

- subscription packaging for source/compliance data
- per-feature usage reporting requirements
- differentiated billing for supplemental nonprofit data routes

### Constraint

Preserve the Phase 20B metric names and route-to-metric mapping for lookup, search, and filings so any future expansion is additive.

## TODO-ARCH-008

### Title

Move premium enrichment gating to a registry-driven feature map for future paid providers.

### Rationale

Phase 20C enforces feature flags for current premium integrations through the existing feature-to-integration mapping. As new paid enrichment providers are added, manually extending per-feature mappings in query orchestration will become harder to maintain.

### Migration Triggers

- onboarding additional premium enrichment providers
- plan-tier specific source packaging
- self-serve premium integration rollout

### Constraint

Keep the Phase 20C nonprofit-service enforcement seam stable so future premium integrations can plug in by extending registry metadata and flag mappings instead of changing nonprofit route contracts.

## TODO-ARCH-009

### Title

Evaluate migrating billing and organization-settings routes onto the centralized tenant authorization middleware.

### Rationale

Phase 20D centralizes tenant authorization for nonprofit, membership, and organization API-key routes. Billing and settings endpoints still need a final decision on how portal organizations, account linkage, and tenant scope should align before they fully share the same middleware contract.

### Migration Triggers

- portal and billing account linkage finalized
- organization settings expanded beyond nonprofit integrations
- need for one consistent org-scope authorization model across all portal routes

### Constraint

Keep the Phase 20D `TenantContext` contract stable so additional organization-scoped routes can adopt the middleware without changing existing nonprofit, membership, or API-key handler contracts.

## TODO-ARCH-010

### Title

Replace the customer-user address-search placeholder with a backend-supported nonprofit discovery workflow.

### Rationale

Phase 20E moves the real tenant-aware nonprofit experience onto the portal workspace route using the backend-supported EIN and name search endpoints. The older customer-user address-search placeholder remains out of scope until the platform exposes a real address or richer organization discovery API.

### Migration Triggers

## TODO-ARCH-028

### Title

Retire remaining legacy S3-backed Form 990 orchestration paths after the local/workspace ingest runtime cutover.

### Rationale

The active Form 990 local and ECS-parity ingest path now persists archive and filing metadata directly to PostgreSQL and uses workspace-local artifacts instead of S3 job artifacts. Older orchestration and reconciliation modules still carry S3 manifest, raw XML, and run-store assumptions that are no longer authoritative for the active ingest runtime.

### Migration Triggers

- monthly worker parity requirements
- reconciliation redesign against PostgreSQL archive/file metadata
- retirement of legacy TEOS raw XML and S3 manifest state flows

### Constraint

Do not reintroduce S3-specific runtime contracts into the active archive-at-a-time ingest path; any legacy cleanup should converge the remaining orchestration modules onto the workspace-plus-PostgreSQL model.

### Status

Backend runtime cutover completed for the active Form 990 monthly path:

- retired backend-owned Lambda/S3-era Form 990 runtime hosts and staging shims
- removed S3-shaped monthly worker env requirements from the backend workflow contract
- removed legacy Form 990 manifest/raw-XML helper modules from the backend runtime path
- kept the workspace-plus-PostgreSQL monthly runtime as the only supported backend execution model

- backend address-search support for nonprofit discovery
- customer-user IA refresh for search and review workflows
- need to retire placeholder local datasets from the portal surface

### Constraint

Keep the Phase 20E workspace nonprofit-search contract stable so future address or expanded discovery support can plug into the existing portal organization provider and API client without changing tenant header behavior.

## TODO-ARCH-011

### Title

Define a stable export and warehouse shape for nonprofit access audit analytics.

### Rationale

Phase 20F adds structured audit logging for tenant-aware nonprofit reads and stores analytics-oriented fields inside the audit metadata blob. That is sufficient for in-product auditing and incremental reporting, but downstream export and warehouse consumers may eventually need a stricter schema for durable analytics.

### Migration Triggers

## TODO-ARCH-012

### Title

Retire the legacy TEOS S3 manifest as authoritative processing state once the
remaining Form 990 discovery/runtime paths fully use PostgreSQL archive
metadata.

### Rationale

Phase 27F introduces PostgreSQL-backed archive metadata and extracted-file hash
tracking for the monthly Form 990 task runtime, but broader TEOS discovery and
source-batch orchestration still retain compatibility use of the older S3
manifest state.

### Migration Triggers

- full PostgreSQL-backed TEOS discovery cutover
- removal of manifest-driven TEOS source-batch scheduling
- confirmation that rollback no longer depends on the S3 manifest state

### Constraint

Keep current monthly-task archive/file change detection stable while the TEOS
runtime finishes moving off the compatibility manifest.

### Status

The active backend monthly runtime no longer depends on the TEOS S3 manifest.
Any remaining follow-up is limited to non-backend infra/history cleanup rather
than the current workspace/PostgreSQL ingest path.

- audit log export to a data warehouse or lake
- BI dashboards built on nonprofit access activity
- compliance or customer reporting that depends on stable audit dimensions

### Constraint

Keep the Phase 20F nonprofit audit event taxonomy stable and additive so future export shaping can standardize metadata without breaking existing audit records.

## TODO-ARCH-012

### Title

Decide whether public Stripe pricing should default to tax-inclusive or tax-exclusive presentation.

### Rationale

Phase 21A establishes Stripe as the provisional billing provider, but the customer-facing pricing model still needs a durable default. Tax presentation affects checkout clarity, invoice expectations, and how the product markets plan pricing across regions.

### Migration Triggers

- Stripe Tax rollout
- public pricing page refresh
- multi-region billing launch

### Constraint

Keep the organization-scoped billing model and backend billing abstractions stable so tax presentation can be finalized without changing the Phase 21 subscription service boundaries.

## TODO-ARCH-013

### Title

Define remaining edge-policy semantics for Stripe-backed plan lifecycle management.

### Rationale

Phase 21F locks the core policy:

- upgrades are immediate
- downgrades are next-cycle
- cancellation uses `cancel_at_period_end`

What remains open are edge-policy details such as customer messaging, support-led exceptions, and any future need for explicit resume/cancel endpoints beyond the current single `plan-change` contract.

### Migration Triggers

- customer-facing billing policy publication
- billing policy publication
- support and retention workflow definition

### Constraint

Preserve the Phase 21 organization-scoped subscription model and local pending-plan fields so any future policy refinement remains additive and does not change the current plan-change contract.

## TODO-ARCH-014

### Title

Confirm whether the free tier stays Stripe-less or every organization receives a Stripe customer object.

### Rationale

Phase 21A keeps free-tier billing behavior open. The choice affects onboarding flow complexity, reconciliation expectations, billing data completeness, and when Stripe becomes part of the lifecycle for organizations that never upgrade.

### Migration Triggers

- free-to-paid conversion funnel optimization
- invoice and tax requirements for all organizations
- desire for uniform billing identity across tiers

### Constraint

Keep `organization_id` as the canonical billing scope and treat Stripe identifiers as attached billing state so free-tier onboarding policy can change without redefining organization billing identity.

## TODO-ARCH-015

### Title

Decide whether raw Stripe webhook payloads should be archived outside the control-plane billing event record.

### Rationale

Phase 21E keeps webhook reconciliation replay-safe by persisting structured billing event metadata, outcome, and payload fingerprints in the local billing store. That is sufficient for idempotency and basic auditability, but operational replay or provider-dispute workflows may eventually require durable access to the original webhook payload.

### Migration Triggers

- billing operations needs raw-event replay support
- support workflows require exact provider payload inspection
- compliance or finance reporting needs longer-lived webhook evidence

### Constraint

Keep the Phase 21E local billing event model compact and organization-scoped so any future raw-payload archival is additive and does not change the current webhook reconciliation contract.

## TODO-ARCH-016

### Title

Decide when the portal should expose direct invoice history instead of routing invoice access through the billing portal.

### Rationale

Phase 21G completes the frontend billing management experience using the existing backend-managed billing portal session as the invoice access path. That keeps the customer experience unblocked, but it leaves open whether the product should eventually show invoice rows, download links, and payment history directly inside the portal once the backend exposes a first-class invoice endpoint.

### Migration Triggers

- finance or support workflows require in-portal invoice visibility
- customers expect downloadable invoices without leaving the portal
- backend billing APIs add invoice listing or invoice-detail endpoints

### Constraint

Keep the Phase 21 billing UI and backend billing-session abstractions stable so future direct invoice history support is additive and does not replace the current provider-portal entry point.

## TODO-ARCH-017

### Title

Define the durable refund handling policy for Stripe-backed subscriptions.

### Rationale

Phase 21H keeps billing hardening conservative and explicitly avoids automated refund logic. Support still needs a durable policy for when refunds are allowed, who can authorize them, and whether partial, prorated, or exception-based refunds should be reflected in local billing operations guidance.

### Migration Triggers

- finance or support teams begin processing subscription refunds regularly
- the product publishes external billing terms
- webhook or reconciliation flows need to reflect refund-side accounting events

### Constraint

Keep the organization-scoped billing state model and current Stripe service seams stable so refund policy can be formalized without redesigning subscription identity or plan-change orchestration.

## TODO-ARCH-018

### Title

Define the failed payment grace-period and recovery policy for subscription access.

### Rationale

Phase 21H preserves the current conservative default: `payment_failed` and other past-due states restrict product access without introducing a new automated grace-period workflow. A production rollout still needs an explicit policy for timing, messaging, recovery expectations, and any exceptions for enterprise support handling.

### Migration Triggers

- customer-facing billing policy publication
- support playbook for past-due recovery
- retention or dunning workflow implementation

### Constraint

Keep local subscription state as the entitlement source of truth so any future grace-period policy remains additive and does not bypass the existing billing-status enforcement path.

## TODO-ARCH-019

### Title

Document the billing support runbook for reconciliation, webhook incidents, and manual exceptions.

### Rationale

Phase 21H adds backend reconciliation tooling and stronger billing observability, but production operations still need a support-facing runbook that covers delayed webhooks, reconciliation steps, refund escalation, customer communication, and Stripe-side incident triage.

### Migration Triggers

- controlled production rollout of Stripe billing
- support team onboarding for billing incidents
- finance or ops review of reconciliation workflows

### Constraint

Keep the current admin/support tooling and compact billing event model intact so support-runbook documentation can evolve without requiring a new customer-facing billing API.

## TODO-ARCH-020

### Title

Define the future organization slug-rename workflow and redirect semantics.

### Rationale

Phase 22B adds organization profile management through the existing `/v1/organization/settings` contract but intentionally keeps `slug` read-only. Product and support still need a durable policy for when slug changes are allowed, how collisions are prevented, and whether old slugs should redirect for links, API clients, or customer-facing references.

### Migration Triggers

- customers need self-service workspace or tenant renaming
- slug values become part of durable URLs or external-facing links
- support requests begin requiring manual slug correction or recovery

### Constraint

Keep `organization_id` as the canonical tenant identifier and treat `slug` as mutable presentation metadata so any future rename workflow remains additive and does not redefine organization identity or current organization settings contracts.

## TODO-ARCH-021

### Title

Add historical usage buckets for customer-admin trend views and prior-period comparisons.

### Rationale

Phase 22E exposes current-period org-scoped usage totals through `GET /v1/organization/usage`, but the backend still stores monthly aggregates rather than historical buckets suitable for charts, trend lines, or prior-period comparisons in the customer admin portal.

### Migration Triggers

- the portal adds usage trend charts or month-over-month comparisons
- product needs proactive limit-warning analytics based on prior periods
- customer admins request exportable usage history rather than current-period summaries

### Constraint

Keep organization-scoped usage aggregation authoritative in the backend and extend the existing usage repository/service model instead of inventing frontend-maintained trend history.

## TODO-ARCH-022

### Title

Replace the audit-backed customer support intake with a durable CRM or ticketing integration when operational support workflows mature.

### Rationale

Phase 22H adds a customer-admin support surface and backend support-intake endpoint, but the current implementation intentionally records acknowledged requests through the existing audit/event infrastructure only. That is enough for early customer administration, yet it does not provide agent assignment, threaded communication, SLA tracking, or customer-visible ticket history.

### Migration Triggers

- support volume requires queue management or agent ownership
- customer-facing ticket updates become a product requirement
- CRM or helpdesk tooling is selected for operational support workflows

### Constraint

Keep the `OrganizationSupportService` read and intake contracts stable so CRM, email-delivery, or ticketing backends can replace the current recorded-only implementation without changing the customer-admin portal surface.

## TODO-ARCH-023

### Title

Replace implicit default organization selection with explicit portal organization switching for multi-membership users.

### Rationale

Portal session restore now derives active organization context from backend memberships. Until the portal exposes explicit organization selection, users with multiple active memberships are assigned a temporary default organization based on membership recency.

### Migration Triggers

- first customer with regular multi-organization membership
- need for user-driven organization switching in the portal shell
- support requests caused by incorrect default organization selection

### Constraint

Keep the `GET /v1/auth/me` organization-context contract additive so explicit org selection can override the temporary default without breaking current session restore behavior.

## TODO-ARCH-024

### Title

Backfill and cut over the nonprofit read model from Athena/materialized cache inputs into the PostgreSQL nonprofit schema.

### Rationale

Phase 24E introduces PostgreSQL tables for:

- canonical nonprofit identity
- filing records
- source provenance
- compliance snapshots

That schema is additive only in the current phase. Phase 24G allows
PostgreSQL-backed lookup, search, and filings reads behind an explicit query
backend selector, but the repo still needs a deliberate backfill and final
read-path migration plan for the remaining routes and caches:

- source views
- compliance views
- federal-awards views
- the DynamoDB materialized profile cache
- any historical provider data that is not preserved in the current
  materialized profile snapshot payloads

### Migration Triggers

- nonprofit PostgreSQL backfill tooling
- decision to make PostgreSQL authoritative for some or all nonprofit reads
- need for Postgres-native nonprofit reporting or serving workflows

### Constraint

Keep the current nonprofit route contracts stable so any future cutover swaps
the storage/read path behind the existing service surfaces rather than
changing customer-visible payloads.

## TODO-ARCH-029

### Title

Retire the remaining EO/BMF Athena, Glue, and Lambda deployment scaffolding after the backend PostgreSQL/runtime cutover stabilizes.

### Rationale

The backend runtime now has a local/ECS-style EO/BMF ingest path that writes canonical nonprofit data to PostgreSQL and uses workspace-local CSV artifacts. Infrastructure deployment assets still retain older EO/BMF Lambda, Athena, and Glue assumptions for compatibility and staged rollback.

### Migration Triggers

- deployed EO/BMF workers fully switched to the backend-owned federal-ingest image
- confirmation that PostgreSQL-backed nonprofit reads are authoritative in all target environments
- no remaining operational dependency on the legacy EO/BMF Athena/Glue datasets

### Constraint

Do not break existing deployment rollback paths until the backend EO/BMF PostgreSQL cutover is validated end to end in deployed environments.

## TODO-ARCH-030

### Title

Project canonical Form 990 raw filing content into graph-oriented nodes and edges once graph-backed use cases are ready.

### Rationale

Phase 27Q adds `nonprofit_raw_filings` as the durable parsed Form 990 source of
truth in PostgreSQL using canonical `raw_filing_json` payloads plus normalized
XML content hashes and artifact references. That preserves the full filing for
future replay, but it intentionally defers graph-specific materialization and
form-type-specific semantic extraction.

Follow-on work areas include:

- graph node and edge projection contracts derived from canonical raw filings
- cross-filing person / officer / trustee identity resolution rules
- organization-to-organization relationship extraction from grant, control, and
  related-entity sections
- richer form-type-specific extraction parity for `990`, `990EZ`, `990PF`, and
  `990T`
- retirement of `nonprofit_filings.raw_payload` after internal callers migrate
  to the canonical raw-filing store where appropriate

### Migration Triggers

- first graph database pilot
- need for cross-filing relationship analytics beyond current normalized filing
  metrics
- requirement to query non-normalized filing sections without re-downloading
  IRS XML

### Constraint

Keep the Phase 27Q canonical raw-filing store stable as the replay source of
truth so future graph or richer extraction work projects from
`nonprofit_raw_filings` instead of reintroducing ad hoc XML-fetch assumptions.

## TODO-ARCH-031

### Title

Decide whether portal nonprofit recent-search history should remain session-only or become durable organization-scoped history.

### Rationale

The customer portal currently stores recent nonprofit searches only in local
React state inside the nonprofit search controller. That supports immediate
"run again" convenience within the current browser session, but it does not
survive refreshes, new sessions, or cross-user organization access.

### Migration Triggers

- customer expectations that prior searches persist across sessions
- need for shared organization research history
- support or audit requests for durable nonprofit search recall

### Constraint

Keep the current nonprofit search route contracts stable; any durable history
should be additive rather than changing the existing search response payloads.

## TODO-ARCH-032

### Title

Complete the portal UI migration from bespoke form/feedback primitives to Mantine equivalents.

### Rationale

The authenticated portal still mixes Mantine shell/table/menu primitives with a
large custom layer for:

- form fields and button treatments
- inline notice/feedback surfaces
- detail lists and usage summary cards
- page-specific layout treatments in `frontend/portal/src/app.css`

That inconsistency is now causing duplicated styling work, browser-native
dropdown regressions, and uneven interaction patterns across the product.

### Migration Triggers

- replacing remaining native or custom-styled form controls with Mantine inputs
- consolidating section notifications onto dismissible Mantine alert patterns
- retiring portal-specific button/input CSS where Mantine variants are sufficient

### Constraint

Preserve current route behavior and payload contracts while moving presentation
surfaces onto Mantine components incrementally.

### Status

The main portal UI migration is now largely complete:

- introduced shared portal Mantine wrappers for buttons, detail lists, and metric cards
- converted portal notices, error/loading states, and toast surfaces onto Mantine-backed primitives
- migrated sign-in, registration, onboarding, support, settings, API key, usage/billing, nonprofit search, and customer-user pages away from bespoke form/input/button styling
- removed the remaining custom form/detail/action treatments from team management, dashboard activity, profile context, nonprofit embedded detail, and customer-user automation credential cards
- flattened authenticated portal sections onto a borderless header-and-divider layout so section shells no longer read as nested cards
- simplified detail lists and subscription metadata into lighter multi-column text layouts instead of boxed pill grids
- added explicit browser-local save actions for editable customer profile sections that previously had mutable controls without a commit point
- kept a small set of portal-local classes only for shell/layout structure, stacked section dividers, and toast positioning

## TODO-ARCH-033

### Title

Finish the dedicated nonprofit-database migration and schema-management flow after the runtime split.

### Rationale

The runtime can now isolate nonprofit/Form 990 data onto a dedicated PostgreSQL
endpoint so scheduled ingest failures or maintenance on the nonprofit data plane
do not share a database with customer accounts, subscriptions, billing events,
or organization settings.

The remaining follow-on work is operational rather than service-contract
shape:

- dedicated deployment wiring and secrets for the nonprofit PostgreSQL endpoint
- nonprofit-specific migration/bootstrap tooling beyond the current runtime
  table bootstrap helper
- data migration/cutover planning for existing shared-database nonprofit rows in
  environments that already co-locate nonprofit and customer data

### Migration Triggers

- first deployed environment that uses separate PostgreSQL databases for
  control-plane and nonprofit data
- nonprofit schema revisions that need first-class migration history instead of
  bootstrap `create_all` semantics
- operational runbooks for independent backup, restore, or failover of the
  nonprofit data plane

### Constraint

Keep the existing customer-account, billing, nonprofit query, and ingest
service contracts stable while the schema-management path for the dedicated
nonprofit database is hardened.

### Status

Dev-focused completion is now in place:

- dedicated nonprofit Alembic history exists under `alembic_nonprofit/`
- backend local-dev commands now support nonprofit revision inspection,
  destructive reset, and destructive cutover into a dedicated nonprofit
  database
- Terraform/runtime env wiring now carries dedicated nonprofit host, secret,
  and backend-selector settings for Lambda/ECS runtimes

The remaining work, if any, is production rollout policy rather than code-path
completion.

## TODO-ARCH-025

### Title

Standardize deployed PostgreSQL connectivity and enablement policy for nonprofit ingest workers.

### Rationale

Phase 24F adds an opt-in PostgreSQL nonprofit ingest persistence path, but the
current deployment posture is still mixed:

- nonprofit ingest discovery and staging artifacts remain S3-backed
- Athena and the materialized profile cache still serve nonprofit reads
- not every ingest entrypoint environment is guaranteed to have PostgreSQL
  network/secrets wiring enabled yet

### Migration Triggers

- enabling `PLATFORM_NONPROFIT_STORE_BACKEND=postgres` in deployed ingest
  environments
- making PostgreSQL-backed nonprofit ingest persistence authoritative rather
  than optional
- aligning Lambda/ECS worker DB connectivity with the current query/runtime
  PostgreSQL posture

### Constraint

Keep the new nonprofit ingest persistence hook additive so environments can
enable PostgreSQL-backed nonprofit writes deliberately without breaking the
existing S3 manifest and artifact flow.

## TODO-ARCH-026

### Title

Execute the staged API runtime migration from API Gateway/Lambda to ALB + ECS.

### Rationale

Phase 25A confirms the current HTTP API is still strongly coupled to:

- `infrastructure/lambda_query.py`
- API Gateway REST resources and integrations
- API Gateway custom-domain routing
- Lambda ZIP packaging and handler-oriented tests

The repo already has ECS/Fargate worker patterns, but it does not yet have a
real ASGI application boundary for the main HTTP API. The runtime pivot
therefore requires a staged extraction and cutover plan rather than a direct
infrastructure swap.

### Migration Triggers

- ASGI-capable application extraction from `lambda_query.py`
- API containerization
- ECS API service and ALB provisioning
- route and auth parity validation
- ingress cutover readiness

### Constraint

Keep `/v1/...` route contracts stable and preserve Lambda/API Gateway as a
rollback path until ECS parity is validated.

### Follow-On Sequence

1. extract a framework-neutral application boundary from `lambda_query.py`
2. introduce an ASGI app factory and keep Lambda as a compatibility adapter
3. add API container packaging and local run support
4. provision ALB + ECS Fargate infrastructure for the API
5. run Lambda/ECS parity validation for routes, auth, CORS, and webhooks
6. cut ingress over from API Gateway custom domain to ALB
7. remove obsolete API-serving Lambda/API Gateway resources after validation

## TODO-ARCH-027

### Title

Refactor Form 990 ingest runtime hosts onto the new workspace-based module seams.

### Rationale

Phase 27E establishes a local-first Form 990 ingest architecture under
`backend/ingest/federal` with explicit module seams for discovery, download,
extract, parse, persist, cleanup, and orchestration plus a deterministic
workspace rooted at `FORM990_WORKSPACE_DIR`.

The live runtime behavior still primarily flows through:

- `backend/ingest/federal/src/verification/backend/ingest/federal/form990/runtime.py`
- `backend/ingest/federal/src/verification/backend/ingest/federal/form990/worker.py`
- `backend/ingest/federal/src/verification/backend/ingest/federal/form990/`

### Migration Triggers

- archive-at-a-time local execution refactor
- richer Form 990 ECS task orchestration
- removal of infrastructure-era batch-processing seams from runtime hosts

### Constraint

Keep current Form 990 payload contracts, S3 manifest behavior, and PostgreSQL
persistence hooks stable while moving archive lifecycle responsibilities behind
the new workspace-oriented modules.

## TODO-ARCH-100

### Title

Restore PostgreSQL peer benchmark parity for nonprofit verification lookups.

### Rationale

The nonprofit lookup path now derives Form 990 enrichment directly from
`nonprofit_filings.raw_payload` in PostgreSQL, but peer benchmark aggregation is
still Athena-specific. Local and ECS PostgreSQL-first runtimes should gain a
datastore-native benchmark implementation so score behavior no longer depends on
Athena availability.

## TODO-ARCH-101

### Title

Execute the hard Form 990 cutover away from Athena, Glue, and S3 onto a
PostgreSQL-plus-workspace runtime.

### Rationale

The active backend Form 990 processing path is already largely local-workspace
and PostgreSQL-oriented, but the repo still retains meaningful legacy coupling
in:

- API/runtime Athena client construction and selector wiring
- Form 990 ops metadata stored through `S3RunStore`
- S3-shaped monthly ingest workflow contracts and docs
- Terraform Athena workgroups, Glue tables, Form 990 S3 bucket/prefix wiring,
  and broad IAM grants

This follow-on should be treated as a hard cutover rather than a compatibility
phase. Once complete, no supported Form 990 runtime or deployment path should
depend on Athena, Glue, or S3.

### Migration Triggers

- PostgreSQL query parity for remaining Form 990 read behavior
- replacement or retirement of S3-backed Form 990 ops/run metadata
- decision to delete legacy Form 990 AWS resources rather than keep rollback
  selectors

### Constraint

Do not preserve Athena/S3-era Form 990 behavior behind feature flags, backend
selectors, or compatibility shims. The cutover should converge the repo on one
authoritative Form 990 architecture.

## TODO-ARCH-102

### Title

Complete the nonprofit customer-surface cutover from score/recommendation
payloads to advisory copilot semantics.

### Rationale

The portal nonprofit detail route now uses snapshot-backed advisory detail
payloads and versioned advisory artifacts, but legacy verification and policy
internals still expose score- and recommendation-oriented fields in older
customer-visible routes and persisted compatibility shapes.

### Migration Triggers

- retire remaining customer-facing score/recommendation fields from
  `/v1/nonprofit/{ein}` and related compatibility paths
- replace score-driven naming in legacy serving/materialization helpers
- align compliance and evidence payloads with signal/explanation language

### Constraint

Keep internal matching/ranking support implementation-only unless a future
customer-facing use is explicitly approved.

## TODO-ARCH-104

### Title

Evaluate a server-side browser session store after the cookie-backed portal auth cutover.

### Rationale

The current portal login persistence cutover uses a signed browser session cookie
so refreshes survive without depending on localStorage. That keeps the browser
session stateless, but it still leaves the auth token itself embedded in the
cookie value. A later phase may want a true server-side session or memory-store
session model for stricter revocation, rotation, or inspection semantics.

### Migration Triggers

- session revocation or rotation requirements exceed signed-cookie behavior
- operators need server-side session visibility or forced invalidation
- portal auth policy moves away from stateless browser-held credentials

### Constraint

Keep the existing `POST /v1/auth/login`, `POST /v1/auth/register`, `POST /v1/auth/logout`,
and `GET /v1/auth/me` contracts stable so a future session store can replace
the cookie payload without changing the portal surface.

