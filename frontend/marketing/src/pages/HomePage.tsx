import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  Card,
  CallToAction,
  FeatureGrid,
  Grid,
  HeroSection,
  LogoCloud,
} from "@charity-status/shared-ui";
import type { MarketingEndpoints } from "../app/marketingEndpoints";

interface HomePageProps {
  endpoints: MarketingEndpoints;
  platformLoginUrl: string;
  runtimeConfig: FrontendRuntimeConfig;
}

export function HomePage({
  endpoints,
  platformLoginUrl,
  runtimeConfig,
}: HomePageProps) {
  return (
    <div className="marketing-page-stack">
      <HeroSection
        actions={
          <>
            <a className="marketing-shell__cta marketing-shell__cta--primary" href="#/product">
              Explore product
            </a>
            <a className="marketing-shell__cta marketing-shell__cta--secondary" href={platformLoginUrl}>
              Portal login
            </a>
          </>
        }
        description="VerifyForGood gives CSR, grantmaking, and compliance teams a calm way to review nonprofit status, filings, and source-backed evidence before decisions move downstream."
        eyebrow="Trust-forward nonprofit review"
        sideContent={
          <Card title="Platform snapshot">
            <div className="marketing-page-stack">
              <p className="marketing-shell__lede" style={{ margin: 0 }}>
                Shared token-driven styling keeps the portal and marketing site aligned.
              </p>
              <dl className="marketing-shell__details">
                <div>
                  <dt>Search endpoint</dt>
                  <dd>
                    <code>{endpoints.nonprofitSearch}</code>
                  </dd>
                </div>
                <div>
                  <dt>Verification endpoint</dt>
                  <dd>
                    <code>{endpoints.nonprofitVerify}</code>
                  </dd>
                </div>
                <div>
                  <dt>Environment</dt>
                  <dd>{runtimeConfig.environment}</dd>
                </div>
              </dl>
            </div>
          </Card>
        }
        title="Compliance-grade verification without noisy workflows"
      />

      <LogoCloud
        items={[
          "Grantmaking teams",
          "CSR operations",
          "Procurement review",
          "Foundation programs",
        ]}
      />

      <FeatureGrid
        items={[
          {
            eyebrow: "Verification",
            title: "Review nonprofit status with evidence",
            description:
              "Confirm IRS-backed status and inspect filings before teams make eligibility or compliance decisions.",
          },
          {
            eyebrow: "Sources",
            title: "Keep provenance visible",
            description:
              "Surface filing and source context so trust signals stay explainable instead of opaque.",
          },
          {
            eyebrow: "Scalability",
            title: "Grow from first check to team workflow",
            description:
              "Move from one-off reviews into repeatable monitoring, risk review, and API-driven integrations.",
          },
          {
            eyebrow: "Onboarding",
            title: "Start on free with clear boundaries",
            description:
              "Value-forward onboarding keeps usage and upgrade decisions explicit without pressure or hidden state.",
          },
        ]}
      />

      <Grid className="marketing-page-grid">
        <CallToAction
          actions={
            <>
              <a className="marketing-shell__cta marketing-shell__cta--primary" href="#/pricing">
                Review plans
              </a>
              <a className="marketing-shell__cta marketing-shell__cta--secondary" href="#/developers">
                API guide
              </a>
            </>
          }
          description="Public messaging and authenticated product workflows now share the same tokens, spacing rhythm, and component treatment."
          title="Consistent from marketing to portal"
        />
        <Card
          description="Begin on the free tier, keep plan limits visible, and move up only when broader capacity is actually useful."
          title="Start on free"
        />
      </Grid>
    </div>
  );
}
