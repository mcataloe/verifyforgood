import { Inline, Panel } from "@charity-status/shared-ui";
import type { ReactNode } from "react";
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
      <Inline className="portal-form__actions">
        <button
          className="portal-shell__action"
          onClick={onAction}
          type="button"
        >
          {actionLabel}
        </button>
      </Inline>
    ) : null;

  return (
    <Panel subtitle={subtitle} title={title}>
      <PortalNotice action={action} title="Something went wrong" tone="error">
        <p>{message}</p>
      </PortalNotice>
    </Panel>
  );
}
