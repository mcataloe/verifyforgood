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

interface PortalAuthLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  runtimeConfig: FrontendRuntimeConfig;
  subtitle: string;
  title: string;
}

export function PortalAuthLayout({
  app,
  children,
  runtimeConfig,
  subtitle,
  title,
}: PortalAuthLayoutProps) {
  return (
    <Page className="portal-auth-shell">
      <Section className="portal-auth-shell__section">
        <Container size="narrow">
          <div className="portal-auth-shell__stack">
            <div className="portal-auth-shell__hero">
              <p className="portal-shell__eyebrow">Protected Surface</p>
              <h1>{title}</h1>
              <p>{subtitle}</p>

              <Inline className="portal-auth-shell__status-row">
                <span className="portal-shell__status-pill">
                  App: {app.title}
                </span>
                <span className="portal-shell__status-pill">
                  Env: {runtimeConfig.environment}
                </span>
                <span className="portal-shell__status-pill">
                  API: /{runtimeConfig.apiVersion}
                </span>
              </Inline>
            </div>

            <Panel
              title="Portal auth boundary"
              subtitle="Portal routes stay protected, while marketing and docs remain public."
            >
              {children}
            </Panel>
          </div>
        </Container>
      </Section>
    </Page>
  );
}
