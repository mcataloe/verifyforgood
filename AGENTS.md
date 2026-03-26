# AGENTS

## Durable Repo Rules

- Follow the House Standard prompt structure.
- Analyze existing modules before modifying code.
- Preserve backward compatibility.
- Keep changes DRY and modular.
- Prefer service/repository separation.
- Maintain datastore-agnostic interfaces where feasible.
- Update `TODO.md` when discovering deferred work.
- Keep documentation minimal but accurate.
- Favor incremental, testable changes.
- Do not introduce breaking schema changes without migration planning.

## Planning Memory

- Review `AGENTS.md` before substantial implementation work.
- Review `TODO.md` for deferred architecture and follow-up items.
- Review relevant documents in `docs/architecture/` and `docs/implementation/` before multi-step feature work.
- Store architectural decisions in `docs/architecture/`.
- Store evolving implementation plans and progress notes in `docs/implementation/`.
- Update status documentation when implementation progress meaningfully changes.
