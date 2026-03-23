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
  - `SidebarProfileSection`
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
- storybook-style example fixtures:
  - `CorePrimitivesExamples`
  - `FeedbackStatesExamples`
  - `OnboardingFlowExamples`
  - `NavigationStatesExamples`

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
        helpText:
          "High-level product activity and recent verification signals.",
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

Sidebar structure responsibilities:

- the shared shell owns the overall sidebar frame:
  - app/header area
  - scrollable grouped navigation content
  - footer/profile slot
- downstream apps should pass already-filtered navigation into the shell and keep permission logic out of rendering components
- downstream apps can provide a `sidebarSummary` slot when they need a compact branded header summary above the links
- downstream apps can customize the footer slot for context/profile content without changing the shared sidebar layout contract
- `SidebarProfileSection` is the compact shared footer/profile primitive for organization or account context only; appearance controls should live on a profile or settings surface instead of the sidebar footer

Footer/profile metadata expectations:

- `primaryLabel`: required top-line identity such as organization or workspace name
- `secondaryLabel`: optional compact account/workspace identifier
- `tertiaryLabel`: optional user display name or secondary identity line
- `accessLabel`: optional short badge-like access descriptor supplied by the consuming app
- `action`: optional lightweight footer action such as a profile/settings link when the consuming app wants to connect identity context back to a user-owned preferences surface
- `ColorSchemeToggle` remains available for profile or settings surfaces that need local appearance preferences, but it should not be treated as sidebar content

Nested navigation behavior assumptions:

- keep `label` concise and scannable; use `helpText` for short tooltip metadata instead of inline descriptions in the nav list
- labels should remain understandable on their own without requiring extra affordances to make sense
- keep role-restricted items hidden; use locked plan behavior only when discovery is useful and the destination should remain visibly unavailable
- choose `planRestrictedBehavior: "hidden"` when a feature should stay out of the information architecture for lower tiers
- choose `planRestrictedBehavior: "locked"` when a feature should remain discoverable for upgrade awareness and should include clear availability copy in `helpText`
- section and item `helpText` are exposed through tooltip/aria metadata rather than persistent inline copy inside the sidebar
- locked items render as disabled rows, do not navigate, and expose their availability copy through tooltip/aria metadata
- items with `children` render as expandable groups in the sidebar
- active descendants automatically open and highlight their parent group
- if a parent has only one visible child after upstream filtering, the group opens automatically
- if you need a navigable overview route for a parent group, prefer an explicit first child item instead of relying on the parent row itself

## Navigation fixture example

`NavigationStatesExamples` is the lightweight contributor fixture for shell work when Storybook is not present in the workspace.

It is intended to make these states easy to inspect locally:

- developer
- portal admin
- customer admin
- customer user
- locked plan-gated API access
- light and dark mode

The fixture deliberately uses nested groups so contributors can inspect parent expansion and active-descendant behavior even while the current portal information architecture remains relatively shallow.

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
