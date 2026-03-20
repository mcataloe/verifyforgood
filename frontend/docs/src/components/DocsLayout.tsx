import { Page, Panel } from "@charity-status/shared-ui";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";
import type { DocsRouteDefinition } from "../app/docsRoutes";

interface DocsLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  currentRoute: DocsRouteDefinition;
  routes: DocsRouteDefinition[];
  runtimeConfig: FrontendRuntimeConfig;
}

export function DocsLayout({
  app,
  children,
  currentRoute,
  routes,
  runtimeConfig,
}: DocsLayoutProps) {
  return (
    <Page className="docs-shell">
      <aside className="docs-shell__sidebar">
        <div className="docs-shell__intro">
          <p className="docs-shell__eyebrow">Documentation Surface</p>
          <h1>{app.title}</h1>
          <p>{app.description}</p>
        </div>

        <nav className="docs-shell__nav" aria-label="Documentation navigation">
          {routes.map((route) => (
            <a
              key={route.key}
              className={
                route.key === currentRoute.key
                  ? "docs-shell__nav-link docs-shell__nav-link--active"
                  : "docs-shell__nav-link"
              }
              href={route.hash}
            >
              <span>{route.label}</span>
              <small>{route.description}</small>
            </a>
          ))}
        </nav>

        <Panel
          title="Current build context"
          subtitle="Docs remain content-focused and deployment-light."
        >
          <dl className="docs-shell__details">
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
      </aside>

      <main className="docs-shell__main">
        <header className="docs-shell__header">
          <p className="docs-shell__eyebrow">Current Section</p>
          <h2>{currentRoute.label}</h2>
          <p>{currentRoute.description}</p>
        </header>

        <section className="docs-shell__content">{children}</section>
      </main>
    </Page>
  );
}
