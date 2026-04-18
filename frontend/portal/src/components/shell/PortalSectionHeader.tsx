import type { ReactNode } from "react";

interface PortalSectionHeaderProps {
  action?: ReactNode;
  description?: string;
  eyebrow?: string;
  title: string;
}

export function PortalSectionHeader({
  action,
  description,
  title,
}: PortalSectionHeaderProps) {
  return (
    <div className="portal-section-header">
      <div className="portal-section-header__copy">
        <h2>{title}</h2>
        {description ? (
          <p className="portal-section-header__description">{description}</p>
        ) : null}
      </div>
      {action ? <div className="portal-section-header__action">{action}</div> : null}
    </div>
  );
}
