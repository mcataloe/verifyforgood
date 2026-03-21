import { Panel } from "@charity-status/shared-ui";
import type { PropsWithChildren } from "react";
import { PortalNotice } from "./PortalNotice";

interface PortalLoadingStateProps extends PropsWithChildren {
  subtitle: string;
  title: string;
}

export function PortalLoadingState({
  children,
  subtitle,
  title,
}: PortalLoadingStateProps) {
  return (
    <Panel subtitle={subtitle} title={title}>
      <PortalNotice title="Loading" tone="loading">
        {children}
      </PortalNotice>
    </Panel>
  );
}
