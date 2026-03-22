import { CallToAction, FeatureGrid } from "@charity-status/shared-ui";

export function ProductPage() {
  return (
    <div className="marketing-page-stack">
      <FeatureGrid
        items={[
          {
            eyebrow: "Core workflow",
            title: "Verification by EIN or organization name",
            description:
              "Move from a simple lookup to a structured review experience with entity detail, filings, and source visibility.",
          },
          {
            eyebrow: "Entity review",
            title: "Readable detail screens",
            description:
              "Shared summary cards, status badges, tabs, and table patterns keep trust cues consistent across screens.",
          },
          {
            eyebrow: "Operations",
            title: "Data-heavy surfaces without clutter",
            description:
              "Reusable table filters, pagination, and loading/empty/error states are designed for organization-heavy workflows.",
          },
          {
            eyebrow: "Expansion",
            title: "Ready for onboarding and integration flows",
            description:
              "The design system now supports welcome flows, API setup, and team invitations without a separate visual language.",
          },
        ]}
      />

      <CallToAction
        actions={
          <a className="marketing-shell__cta marketing-shell__cta--secondary" href="#/login">
            Open portal
          </a>
        }
        description="Future product tours and segment-specific proof points can build on these shared surfaces instead of reintroducing one-off page patterns."
        title="Product storytelling now shares the platform foundation"
      />
    </div>
  );
}
