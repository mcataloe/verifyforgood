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
      { key: "dashboard", label: "Dashboard", href: "#/dashboard" },
      {
        key: "organizations",
        label: "Organizations",
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
