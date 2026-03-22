import {
  ColorSchemeToggle,
  Container,
  Page,
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

            <div className="marketing-shell__toolbar">
              <ColorSchemeToggle />
            </div>
          </div>

          <div className="marketing-shell__context">
            <span>{app.audience}</span>
            <span>{runtimeConfig.environment}</span>
            <span>{runtimeConfig.apiVersion}</span>
          </div>
        </Container>
      </Section>

      <Section className="marketing-shell__main">
        <Container size="wide">{children}</Container>
      </Section>
    </Page>
  );
}
