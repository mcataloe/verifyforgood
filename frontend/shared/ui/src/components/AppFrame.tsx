import type { PropsWithChildren } from "react";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { formatSurfaceLabel } from "@charity-status/shared-utils";

type AppFrameProps = PropsWithChildren<{
  app: FrontendAppInfo;
  eyebrow: string;
}>;

export function AppFrame({ app, children, eyebrow }: AppFrameProps) {
  return (
    <main className="app-frame">
      <section className="app-frame__panel">
        <p className="app-frame__eyebrow">{eyebrow}</p>
        <div className="app-frame__meta">
          <span>{formatSurfaceLabel(app.surface)}</span>
          <span>{app.audience}</span>
        </div>
        <h1>{app.title}</h1>
        <p className="app-frame__description">{app.description}</p>
        <div className="app-frame__content">{children}</div>
      </section>
    </main>
  );
}
