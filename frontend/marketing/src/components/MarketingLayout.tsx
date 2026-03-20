import {
  Container,
  Inline,
  Page,
  Panel,
  Section,
} from "@charity-status/shared-ui";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import type { MarketingRouteDefinition } from "../app/marketingRoutes";

interface MarketingLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  currentRoute: MarketingRouteDefinition;
  routes: MarketingRouteDefinition[];
  runtimeConfig: FrontendRuntimeConfig;
}

export function MarketingLayout({
  app,
  children,
  currentRoute,
  routes,
  runtimeConfig,
}: MarketingLayoutProps) {
  return (
    <Page className="marketing-shell">
      <Section className="marketing-shell__hero">
        <Container size="wide">
          <div className="marketing-shell__topbar">
            <a className="marketing-shell__brand" href="#/home">
              <span className="marketing-shell__brand-mark">V</span>
              <span>VerifyForGood</span>
            </a>

            <nav
              className="marketing-shell__nav"
              aria-label="Marketing site navigation"
            >
              {routes.map((route) => (
                <a
                  key={route.key}
                  className={
                    route.key === currentRoute.key
                      ? "marketing-shell__nav-link marketing-shell__nav-link--active"
                      : "marketing-shell__nav-link"
                  }
                  href={route.hash}
                >
                  {route.label}
                </a>
              ))}
            </nav>
          </div>

          <div className="marketing-shell__hero-grid">
            <div className="marketing-shell__hero-copy">
              <p className="marketing-shell__eyebrow">Public Surface</p>
              <h1>{app.title}</h1>
              <p className="marketing-shell__lede">{app.description}</p>
              <Inline className="marketing-shell__cta-row">
                <a
                  className="marketing-shell__cta marketing-shell__cta--primary"
                  href="#/product"
                >
                  Explore product
                </a>
                <a
                  className="marketing-shell__cta marketing-shell__cta--secondary"
                  href="#/login"
                >
                  Portal login
                </a>
              </Inline>
            </div>

            <Panel title="Current page" subtitle={currentRoute.description}>
              <dl className="marketing-shell__details">
                <div>
                  <dt>Audience</dt>
                  <dd>{app.audience}</dd>
                </div>
                <div>
                  <dt>Environment</dt>
                  <dd>{runtimeConfig.environment}</dd>
                </div>
                <div>
                  <dt>API version</dt>
                  <dd>{runtimeConfig.apiVersion}</dd>
                </div>
              </dl>
            </Panel>
          </div>
        </Container>
      </Section>

      <Section className="marketing-shell__main">
        <Container size="wide">{children}</Container>
      </Section>
    </Page>
  );
}
