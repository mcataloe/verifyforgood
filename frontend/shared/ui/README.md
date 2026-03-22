# Shared UI Package

This package contains the shared VerifyForGood design foundation for the frontend workspace.

## Current scope

- framework-agnostic design tokens in `src/theme/tokens.ts`
- Mantine bridge configuration in `src/theme/mantineTheme.ts`
- light and dark mode support through `VerifyForGoodMantineProvider`
- shared layouts:
  - `VerifyForGoodAppShell`
  - `EntityDetailLayout`
  - onboarding layouts and progress primitives
- shared UI primitives:
  - `PageHeader`
  - `Card`
  - `SectionContainer`
  - `StatusBadge`
  - `LoadingSkeleton`
  - `EmptyState`
  - `ErrorState`
- reusable table patterns:
  - `DataTable`
  - `FilterBar`
- navigation schema and filtering helpers for grouped, nested, role-aware, and plan-aware app navigation
- marketing-aligned sections:
  - `HeroSection`
  - `FeatureGrid`
  - `CallToAction`
  - `LogoCloud`

## Usage expectations

- treat `src/theme/tokens.ts` as the source of truth for color, spacing, radius, shadow, and typography decisions
- derive framework theme adapters from the tokens instead of redefining values in app code
- prefer shared primitives when portal and marketing need the same interaction or layout contract
- keep product data fetching and workflow logic outside this package
- keep navigation configuration declarative and filter it before rendering rather than scattering role/plan checks through layout components

## App shell usage

Prefer `navigationSections` as the primary `VerifyForGoodAppShell` contract.

```tsx
import {
  VerifyForGoodAppShell,
  type VerifyForGoodAppShellNavSection,
} from "@charity-status/shared-ui";

const navigationSections: VerifyForGoodAppShellNavSection[] = [
  {
    key: "core",
    label: "Core",
    helpText: "Primary product destinations.",
    items: [
      {
        key: "dashboard",
        label: "Dashboard",
        helpText: "High-level product activity and recent verification signals.",
        href: "#/dashboard",
      },
      {
        key: "organizations",
        label: "Organizations",
        helpText: "Browse organization review and credential management views.",
        children: [
          { key: "directory", label: "Directory", href: "#/organizations" },
          { key: "sources", label: "Sources", href: "#/organizations/sources" },
        ],
      },
    ],
  },
];

<VerifyForGoodAppShell
  activeNavigationKey="dashboard"
  appName="VerifyForGood Portal"
  navigationSections={navigationSections}
>
  <main>Content</main>
</VerifyForGoodAppShell>;
```

The older flat `navigation` prop still works as a compatibility path and is normalized into one default `Navigation` section.

Nested navigation behavior assumptions:

- keep `label` concise and scannable; use `helpText` for longer tooltip copy instead of inline sidebar descriptions
- labels should remain understandable on their own without requiring the tooltip to make sense
- keep role-restricted items hidden; use locked plan behavior only when discovery is useful and the destination should remain visibly unavailable
- choose `planRestrictedBehavior: "hidden"` when a feature should stay out of the information architecture for lower tiers
- choose `planRestrictedBehavior: "locked"` when a feature should remain discoverable for upgrade awareness and should include clear availability copy in `helpText`
- section `helpText` renders behind a small focusable help trigger next to the section title
- item `helpText` renders as a tooltip on the focusable navigation row when present
- locked items render as disabled rows, do not navigate, and remain keyboard-readable through `aria-describedby`
- items with `children` render as expandable groups in the sidebar
- active descendants automatically open and highlight their parent group
- if a parent has only one visible child after upstream filtering, the group opens automatically
- if you need a navigable overview route for a parent group, prefer an explicit first child item instead of relying on the parent row itself

## Accessibility baseline

- shared themes keep visible focus rings enabled
- status treatments should not rely on color alone
- tables should expose semantic headers and sortable state
- forms and interactive controls should ship with explicit labels by default
- dark mode should use muted slate surfaces instead of pure black backgrounds

## What belongs here

- app-agnostic layout primitives
- reusable, token-driven component foundations
- theme and accessibility defaults that both apps can inherit

## What stays app-local

- marketing-only messaging, conversion copy, and campaign-specific presentation
- portal-only feature wiring, backend integration, and domain workflows
- docs-only content presentation choices that do not generalize
