import { Panel } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
import { PortalActionGroup, PortalButton } from "../PortalPrimitives";
import { PortalNotice } from "./PortalNotice";

interface PortalErrorStateProps {
  actionLabel?: string;
  message: string;
  onAction?: () => void;
  subtitle: string;
  title: string;
}

export function PortalErrorState({
  actionLabel,
  message,
  onAction,
  subtitle,
  title,
}: PortalErrorStateProps) {
  const action: ReactNode =
    actionLabel && onAction ? (
      <PortalActionGroup>
        <PortalButton onClick={onAction} type="button">
          {actionLabel}
        </PortalButton>
      </PortalActionGroup>
    ) : null;

  return (
    <Panel subtitle={subtitle} title={title}>
      <PortalNotice action={action} title="Something went wrong" tone="error">
        <p>{message}</p>
      </PortalNotice>
    </Panel>
  );
}
