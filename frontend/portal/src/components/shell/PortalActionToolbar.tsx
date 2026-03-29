import type { PropsWithChildren } from "react";

interface PortalActionToolbarProps extends PropsWithChildren {
  align?: "split" | "start";
}

export function PortalActionToolbar({
  align = "split",
  children,
}: PortalActionToolbarProps) {
  return (
    <div
      className={`portal-action-toolbar portal-action-toolbar--${align}`}
      role="toolbar"
    >
      {children}
    </div>
  );
}
