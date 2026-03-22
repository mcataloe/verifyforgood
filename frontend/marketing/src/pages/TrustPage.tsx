import { FeatureGrid, LogoCloud } from "@charity-status/shared-ui";

export function TrustPage() {
  return (
    <div className="marketing-page-stack">
      <LogoCloud
        items={[
          "Evidence-backed review",
          "Audit-friendly workflows",
          "Readable dark mode",
          "Accessible defaults",
        ]}
      />
      <FeatureGrid
        items={[
          {
            eyebrow: "Evidence",
            title: "Deterministic review signals",
            description:
              "Trust claims stay anchored to filings, source metadata, and explainable review states rather than generic platform language.",
          },
          {
            eyebrow: "Reliability",
            title: "Clear operational boundaries",
            description:
              "Marketing, portal, and docs remain separate runtimes while sharing the same design tokens and reusable UI primitives.",
          },
          {
            eyebrow: "Accessibility",
            title: "Readable by default",
            description:
              "Contrast, focus visibility, keyboard navigation, and semantic structure are treated as shared defaults instead of page-level exceptions.",
          },
          {
            eyebrow: "Dark mode",
            title: "Calm dark surfaces",
            description:
              "Dark mode avoids pure black backgrounds and keeps tables, tabs, badges, and cards readable across product surfaces.",
          },
        ]}
      />
    </div>
  );
}
