import { Inline, Page, Panel, ThemeRoot } from "@charity-status/shared-ui";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalAuthenticatedSession } from "../app/portalSession";

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
            title="Session boundary"
            subtitle="Mock browser-session state stands in for a future real identity provider."
          >
            <dl className="portal-shell__details">
              <div>
                <dt>User</dt>
                <dd>{session.user.display_name}</dd>
              </div>
              <div>
                <dt>Organization</dt>
                <dd>{session.organization_name}</dd>
              </div>
              <div>
                <dt>Workspace</dt>
                <dd>{session.workspace_id}</dd>
              </div>
              <div>
                <dt>Account</dt>
                <dd>{session.account_id}</dd>
              </div>
              <div>
                <dt>Roles</dt>
                <dd>{session.roles.join(", ")}</dd>
              </div>
            </dl>
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
              Env: {runtimeConfig.environment}
            </span>
            <span className="portal-shell__status-pill">
              Plan: {session.plan}
            </span>
            <span className="portal-shell__status-pill">
              Auth: {session.auth_method.replaceAll("_", " ")}
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
