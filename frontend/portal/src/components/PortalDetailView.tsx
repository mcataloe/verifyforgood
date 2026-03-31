import type { ReactNode } from "react";
import { DetailPageLayout, SectionBlock } from "./shell";

interface PortalDetailViewProps {
  children: ReactNode;
  eyebrow?: ReactNode;
  intro?: ReactNode;
  title: ReactNode;
}

interface PortalDetailSectionProps {
  children: ReactNode;
  intro?: ReactNode;
  title: ReactNode;
}

export function PortalDetailView({
  children,
  eyebrow,
  intro,
  title,
}: PortalDetailViewProps) {
  return (
    <article className="portal-detail-view">
      <header className="portal-detail-view__header">
        {eyebrow ? <p className="portal-shell__eyebrow">{eyebrow}</p> : null}
        <h1>{title}</h1>
        {intro ? <p className="portal-detail-view__intro">{intro}</p> : null}
      </header>
      <DetailPageLayout className="portal-detail-view__sections">
        {children}
      </DetailPageLayout>
    </article>
  );
}

export function PortalDetailSection({
  children,
  intro,
  title,
}: PortalDetailSectionProps) {
  return (
    <SectionBlock className="portal-detail-view__section">
      <div className="portal-detail-view__section-header">
        <h2>{title}</h2>
        {intro ? <p className="portal-detail-view__section-intro">{intro}</p> : null}
      </div>
      <div className="portal-detail-view__section-body">{children}</div>
    </SectionBlock>
  );
}
