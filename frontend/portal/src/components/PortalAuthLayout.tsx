import {
  Container,
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
              <h1>{title}</h1>
              <p>{subtitle}</p>
            </div>

            <Panel
              title={app.title}
              subtitle="Sign in to manage your organization, billing, team access, and verification activity."
            >
              {children}
            </Panel>
          </div>
        </Container>
      </Section>
    </Page>
  );
}
