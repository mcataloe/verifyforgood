import { Grid, Panel } from "@charity-status/shared-ui";
import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import type { MarketingEndpoints } from "../app/marketingEndpoints";

interface HomePageProps {
  endpoints: MarketingEndpoints;
  runtimeConfig: FrontendRuntimeConfig;
}

export function HomePage({ endpoints, runtimeConfig }: HomePageProps) {
  return (
    <Grid className="marketing-page-grid">
      <Panel
        title="What VerifyForGood does"
        subtitle="The public narrative should stay product-first."
      >
        <ul className="marketing-list">
          <li>Verify nonprofit status using IRS and filing-backed data.</li>
          <li>
            Review filings, source evidence, compliance signals, and
            federal-award context.
          </li>
          <li>
            Grow from simple verification into richer monitoring and
            benchmarking workflows.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Why the shell is structured this way"
        subtitle="Ready for messaging and conversion expansion."
      >
        <ul className="marketing-list">
          <li>
            Public messaging stays separate from authenticated portal behavior.
          </li>
          <li>
            Developers, pricing, trust, and contact each have their own IA
            anchor.
          </li>
          <li>
            Shared API/config packages are used without leaking portal
            assumptions into the public site.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Start on free"
        subtitle="Value-forward onboarding without urgency or surprise billing."
      >
        <ul className="marketing-list">
          <li>
            Begin on the free tier and review limits before any paid decision.
          </li>
          <li>
            A time-limited trial can unlock broader workflows later without
            forcing activation at first visit.
          </li>
          <li>
            Paid enrollment stays separate so teams move up only when the
            additional capacity is useful.
          </li>
        </ul>
      </Panel>

      <Panel
        title="Public API glimpse"
        subtitle="Grounded in the current backend contract."
      >
        <p>
          Search currently resolves to <code>{endpoints.nonprofitSearch}</code>{" "}
          and verification to <code>{endpoints.nonprofitVerify}</code> in{" "}
          <strong>{runtimeConfig.environment}</strong>.
        </p>
      </Panel>
    </Grid>
  );
}
