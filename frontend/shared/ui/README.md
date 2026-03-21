# Shared UI Package

This package contains the shared design foundation for the frontend workspace.

## Current scope

- design tokens in `src/theme.css`
  - colors
  - spacing
  - typography
  - radius
  - shadow/elevation
- base theme variables for `default` and `inverse` surfaces
- layout primitives:
  - `Container`
  - `Page`
  - `Section`
  - `Grid`
  - `Inline`
- reusable UI primitives:
  - `AppFrame`
  - `Panel`
  - `ThemeRoot`

## How tokens should be used

- use shared CSS variables from `@charity-status/shared-ui/styles.css` for reusable surfaces and spacing
- build new shared components on semantic theme variables such as panel/background/border/text values
- keep app-level branding choices in app-local CSS, but source repeated values from shared tokens when possible

## What belongs here

- app-agnostic layout primitives
- neutral shared component foundations
- theme and token definitions that all frontend apps can inherit

## What stays app-local

- marketing-only art direction and conversion styling
- portal-only navigation chrome and workflow-specific layouts
- docs-only content presentation choices that do not generalize

## Intentionally deferred

- full component library
- brand-locked visual system
- heavy UI framework adoption
