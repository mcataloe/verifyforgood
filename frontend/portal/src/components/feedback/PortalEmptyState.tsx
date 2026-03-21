import { Panel } from "@charity-status/shared-ui";
import type { PropsWithChildren } from "react";
import { PortalNotice } from "./PortalNotice";

interface PortalEmptyStateProps extends PropsWithChildren {
  subtitle: string;
  title: string;
}

export function PortalEmptyState({
  children,
  subtitle,
  title,
}: PortalEmptyStateProps) {
  return (
    <Panel subtitle={subtitle} title={title}>
      <PortalNotice title="Nothing to show yet" tone="empty">
        {children}
      </PortalNotice>
    </Panel>
  );
}
