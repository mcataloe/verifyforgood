# Advisory Copilot Product Doctrine

## Status

accepted

## Decision

The nonprofit product surface must behave as an advisory copilot, not as a
ratings engine, rankings engine, or recommendation engine.

Customer-facing nonprofit APIs and UI flows must prioritize:

- source facts
- derived signals
- explanations
- strengths, risks, and data gaps
- user-directed comparison and exploration

Customer-facing nonprofit APIs and UI flows must avoid presenting:

- composite platform-owned scores as product truth
- final recommendations or endorsements
- leaderboard framing
- "best", "top", or "winner" language

## Context

The repository retains older verification and policy seams that were built
around scoring, decision, and recommendation payloads. Those internals may
still exist as implementation details or compatibility surfaces, but they do
not define the intended customer product.

The portal nonprofit detail experience is now being reworked around:

- snapshot-backed nonprofit-global detail reads
- signal-based explanation blocks
- explicit data-gap and uncertainty visibility
- human decision ownership

## Consequences

- New customer-facing nonprofit detail contracts should expose facts, signals,
  explanations, and missing-data indicators instead of composite scores or
  recommendation fields.
- Internal ranking or scoring may remain only as a hidden implementation
  mechanism for search relevance, matching, clustering, or deduplication.
- Versioned advisory artifacts may persist richer signal analysis, but they
  must also avoid customer-facing endorsement semantics.
- Follow-on cleanup should keep moving legacy score/recommendation naming out of
  customer-facing nonprofit routes and persisted serving shapes.
