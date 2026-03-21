import { Inline, Page, Panel, ThemeRoot } from "@charity-status/shared-ui";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import { usePortalOrganization } from "../organization/usePortalOrganization";

interface PortalLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  currentRoute: PortalRouteDefinition;
  onSignOut: () => Promise<void>;
  routes: PortalRouteDefinition[];
  runtimeConfig: FrontendRuntimeConfig;
  session: PortalAuthenticatedSession;
}

export function PortalLayout({
  app,
  children,
  currentRoute,
  onSignOut,
  routes,
  runtimeConfig,
  session,
}: PortalLayoutProps) {
  const organization = usePortalOrganization();

  return (
    <Page className="portal-shell">
      <aside className="portal-shell__sidebar">
        <div className="portal-shell__sidebar-copy">
          <p className="portal-shell__eyebrow">Authenticated Surface</p>
          <h1>{app.title}</h1>
          <p>{app.description}</p>
        </div>

        <nav className="portal-shell__nav" aria-label="Portal navigation">
          {routes.map((route) => (
            <a
              key={route.key}
              className={
                route.key === currentRoute.key
                  ? "portal-shell__nav-link portal-shell__nav-link--active"
                  : "portal-shell__nav-link"
              }
              href={route.hash}
            >
              <span>{route.label}</span>
              <small>{route.description}</small>
            </a>
          ))}
        </nav>

        <ThemeRoot tone="inverse">
          <Panel
            title="Active organization context"
            subtitle="The portal now treats workspace and account scope as the primary boundary for future product actions."
          >
            <dl className="portal-shell__details">
              <div>
                <dt>Organization</dt>
                <dd>{organization.activeOrganization.organization_name}</dd>
              </div>
              <div>
                <dt>Workspace</dt>
                <dd>{organization.activeOrganization.workspace_id}</dd>
              </div>
              <div>
                <dt>Account</dt>
                <dd>{organization.activeOrganization.account_id}</dd>
              </div>
              <div>
                <dt>Context source</dt>
                <dd>{organization.activeOrganization.scope_source}</dd>
              </div>
              <div>
                <dt>Roles</dt>
                <dd>{session.roles.join(", ")}</dd>
              </div>
            </dl>
            <p className="portal-shell__context-note">
              Signed in as {session.user.display_name}. Future portal requests
              should flow through the organization-scoped portal API client.
            </p>
          </Panel>
        </ThemeRoot>
      </aside>

      <div className="portal-shell__main">
        <header className="portal-shell__header">
          <div>
            <p className="portal-shell__eyebrow">Current Area</p>
            <h2>{currentRoute.label}</h2>
            <p>{currentRoute.description}</p>
          </div>

          <Inline className="portal-shell__status-row">
            <span className="portal-shell__status-pill">
              Org: {organization.activeOrganization.organization_name}
            </span>
            <span className="portal-shell__status-pill">
              Env: {runtimeConfig.environment}
            </span>
            <span className="portal-shell__status-pill">
              Plan: {session.plan}
            </span>
            <span className="portal-shell__status-pill">
              Auth: {session.auth_method.replaceAll("_", " ")}
            </span>
            <span className="portal-shell__status-pill">
              Scope: {organization.status}
            </span>
            <button
              className="portal-shell__action"
              onClick={() => void onSignOut()}
              type="button"
            >
              Sign out
            </button>
          </Inline>
        </header>

        <section className="portal-shell__content">{children}</section>
      </div>
    </Page>
  );
}
