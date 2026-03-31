import { PageHeader } from "@charity-status/shared-ui";
import type { HTMLAttributes, PropsWithChildren, ReactNode } from "react";

interface PortalPageShellProps
  extends PropsWithChildren,
    Omit<HTMLAttributes<HTMLDivElement>, "title"> {
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
  ...rest
}: PortalPageShellProps) {
  return (
    <div
      className="portal-authenticated-container portal-dashboard portal-page-shell"
      data-testid="portal-page-container"
      {...rest}
    >
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
