import { CloseButton } from "@mantine/core";
import { useState, type PropsWithChildren, type ReactNode } from "react";

interface PortalNoticeProps extends PropsWithChildren {
  action?: ReactNode;
  dismissible?: boolean;
  onDismiss?: () => void;
  title?: string;
  tone: "empty" | "error" | "loading" | "warning";
}

export function PortalNotice({
  action,
  children,
  dismissible = true,
  onDismiss,
  title,
  tone,
}: PortalNoticeProps) {
  const [dismissed, setDismissed] = useState(false);

  if (dismissed) {
    return null;
  }

  return (
    <div
      className={`portal-notice portal-notice--${tone}`}
      role={tone === "error" ? "alert" : "status"}
    >
      <div className="portal-notice__main">
        <div className="portal-notice__content">
          {title ? <p className="portal-notice__title">{title}</p> : null}
          <div className="portal-notice__body">{children}</div>
        </div>
        {dismissible ? (
          <CloseButton
            aria-label={`Dismiss ${title ?? "notification"}`}
            className="portal-notice__dismiss"
            onClick={() => {
              setDismissed(true);
              onDismiss?.();
            }}
          />
        ) : null}
      </div>
      {action ? <div className="portal-notice__action">{action}</div> : null}
    </div>
  );
}
