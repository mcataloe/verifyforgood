<!--
LEAP_DOC_METADATA:
  audience: user, maintainer, agent, contributor
  doc_type: source-of-truth-policy
  authority: canonical
  applies_to: verifyforgood
END_LEAP_DOC_METADATA
-->

# VerifyForGood Source-of-Truth Policy

Status: Active canonical governance policy  
Owner / approver: Project owner  
Last reconciled: 2026-07-02  
Canonical owner of: Documentation precedence, ownership, lifecycle, and conflict handling  
Related Initiatives: `INIT-009`

## Governing Principle

Customers own the meaning and final use of verified, eligible, approved, denied, manual-review, and insufficient-data outcomes for their workflows. VerifyForGood owns source processing, normalization, provenance, derived signals, evidence assembly, and deterministic execution of an applicable customer-selected or customer-defined policy.

## Source Precedence

Use the highest applicable source:

1. Explicit project-owner decisions and ratified governing documents.
2. The Project Charter and Decision Authority document.
3. Current merged code, tests, schemas, and public contracts for implemented behavior.
4. Ratified ADRs and current Architecture documents for technical structure.
5. Strategic Outcomes and Initiative registry for strategic intent and coordinated work.
6. Roadmap for timing, priority, milestones, and sequencing only.
7. Domain map for persistent responsibility boundaries.
8. Delivery Unit and Build Unit records for bounded delivery and implementation.
9. Current implementation plans and status records.
10. Historical Phase and planning records.
11. Stale, superseded, archived, or do-not-use documents.

A lower-precedence source cannot silently override a higher-precedence source.

## Truth Ownership

| Truth | Canonical owner |
|---|---|
| Mission, boundaries, governing principles | Project Charter |
| Customer decision authority | Decision Authority document |
| Documentation precedence and lifecycle | This document |
| Desired observable changes | Strategic Outcomes |
| Temporary coordinated work | Initiative registry and Initiative records |
| Timing and priority | Roadmap |
| Persistent responsibilities | Domain map and Domain records |
| Technical structure | Architecture documents and ADRs |
| Releasable/adoptable increments | Delivery Unit records |
| Bounded implementation work | Build Unit records or approved LEAP Prompts |
| Actual implementation state | Merged code, tests, schemas, routes, contracts, and deployed evidence when available |
| Historical implementation | Historical plans, commits, and Phase records |
| Known conflicts and unresolved drift | Drift ledger and gap register |

No two canonical documents should own the same truth.

## Status and Authority

- **Canonical** — ratified owner for a defined truth.
- **Approved principle** — explicit project-owner decision that governs related Draft work.
- **Draft** — proposed content awaiting ratification.
- **Supporting** — evidence or guidance that does not own strategic truth.
- **Provisional** — current direction or decision not yet ratified.
- **Historical** — preserved record of past planning or implementation.
- **Stale** — contradicted by newer evidence.
- **Do not use** — must not be used for current decisions.
- **Superseded** — intentionally replaced by identified current source truth.

Generated planning documents remain Draft until a human owner ratifies them. Merging a file does not by itself ratify its product or Architecture decisions.

## Repository Reality

When documentation conflicts with current implementation, repository reality is the operational authority for what the system currently does. The conflict must still be recorded; current implementation does not automatically become approved product intent.

Distinguish:

- **documented intent**
- **implemented behavior**
- **inferred behavior**
- **stale behavior**
- **unknown behavior**
- **conflicting evidence**

## Conflict Resolution

When sources conflict:

1. Record the conflict in the drift ledger.
2. Inspect code, tests, schemas, contracts, current Architecture, and relevant history.
3. Identify which document should own the truth.
4. Mark unsupported sources Draft, stale, historical, superseded, or do not use as evidence warrants.
5. Preserve the old path when moving or deleting it would break traceability or compatibility.
6. Stop for a human decision when the conflict changes product meaning, Architecture, public contracts, verification semantics, legal/compliance claims, money, identity, privacy, security, or user trust.

## Customer Decision Authority Precedence

The approved customer decision-authority principle governs ambiguous product wording. Current API fields such as `score_explanation.eligibility`, `decision.status`, and `final_recommendation` remain implemented contracts, but their names do not grant VerifyForGood universal decision authority.

When documenting these fields:

- identify whether the value is a source fact, normalized fact, derived signal, baseline evaluation, policy result, or customer determination
- identify the policy and evidence context
- do not convert a platform output into an unsupported legal or compliance conclusion
- preserve compatibility names until a separately approved contract transition exists

## Roadmap, Domains, and Architecture

- Roadmaps schedule and prioritize work; they do not define Initiative identity.
- Domains persist across roadmap cycles; they are not temporary Initiatives.
- Architecture describes technical structure; it does not define strategic outcomes.
- Historical Phases remain chronological or historical records unless evidence supports another semantic classification.

## Historical, Stale, and Archived Documents

Historical documents may remain useful evidence but do not automatically govern current work. Stale and do-not-use documents must be listed in the stale-document register. Archive or deletion occurs only after replacement source truth exists, links are validated, and the project owner approves the action.

## Ratification

The project owner ratifies Charter, Strategic Outcome, Initiative, and material Architecture decisions. Until ratified, such content must remain visibly Draft or Provisional. The customer decision-authority principle is already approved and must not be weakened without an explicit project-owner decision.
