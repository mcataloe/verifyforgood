# Frontend Detail Body Readability

## Summary

Portal and marketing detail bodies now follow one readability rule: once a user is inside a detail section, the content must stay in a single reading flow.

## Rule

- Use portal `DetailPageLayout`, `SectionBlock`, and `SectionDivider` for detail-page section flow.
- Do not nest `EntityDetailLayout` inside another detail section.
- Do not introduce nested cards, tab frames, bordered sub-panels, or side-by-side subsection columns inside a detail body.
- Use shared `DetailStack` and `DetailFieldList` primitives for embedded detail content.
- Keep forms in detail bodies single-column unless there is a strong accessibility reason to do otherwise.

## Current Application

- Customer-user organization drill-in on the search page uses an embedded stacked detail body.
- Customer-user profile and automation panes avoid outlined inner cards and multi-column subsection layouts.
- Portal organization onboarding, nonprofit review, and settings now use the shared single-column detail layout contract.

## Do Not Regress

- Detail pages must render through `DetailPageLayout`, `SectionBlock`, and `SectionDivider`, and major sections must stay in one single-column stacked flow.
- Authenticated portal surfaces must use the shared wide responsive container pattern instead of narrow marketing-width shells.
- Authentication must happen before organization creation.
- Organization onboarding is conditional and protected, not the default landing page.
- Standard application modals require explicit dismissal and must not close from outside-click or `Escape` unless a documented exception opts in.
- For customer-facing portal wording, follow [`portal-ux-copy-rules.md`](/d:/Repos/charity-status-api/docs/implementation/portal-ux-copy-rules.md).
