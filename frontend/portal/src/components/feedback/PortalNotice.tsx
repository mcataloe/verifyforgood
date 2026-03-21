import type { PropsWithChildren, ReactNode } from "react";

interface PortalNoticeProps extends PropsWithChildren {
  action?: ReactNode;
  title?: string;
  tone: "empty" | "error" | "loading" | "warning";
}

export function PortalNotice({
  action,
  children,
  title,
  tone,
}: PortalNoticeProps) {
  return (
    <div className={`portal-notice portal-notice--${tone}`}>
      {title ? <p className="portal-notice__title">{title}</p> : null}
      <div className="portal-notice__body">{children}</div>
      {action ? <div className="portal-notice__action">{action}</div> : null}
    </div>
  );
}
