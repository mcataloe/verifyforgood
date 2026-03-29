import { PageHeader } from "@charity-status/shared-ui";
import type { PropsWithChildren, ReactNode } from "react";

interface PortalPageShellProps extends PropsWithChildren {
  description: string;
  eyebrow?: string;
  toolbar?: ReactNode;
  title: string;
}

export function PortalPageShell({
  children,
  description,
  eyebrow,
  title,
  toolbar,
}: PortalPageShellProps) {
  return (
    <div className="portal-dashboard portal-page-shell">
      <PageHeader
        description={description}
        eyebrow={eyebrow}
        title={title}
      />
      {toolbar ? <div className="portal-page-shell__toolbar">{toolbar}</div> : null}
      <div className="portal-page-shell__content">{children}</div>
    </div>
  );
}
