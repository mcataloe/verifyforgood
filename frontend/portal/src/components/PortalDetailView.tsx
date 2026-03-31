import { Children, Fragment, type ReactNode } from "react";
import { DetailPageLayout, SectionBlock, SectionDivider } from "./shell";

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
  const sections = Children.toArray(children);

  return (
    <DetailPageLayout
      eyebrow={eyebrow}
      intro={intro}
      title={title}
    >
      {sections.map((section, index) => (
        <Fragment key={`portal-detail-section-${index}`}>
          {section}
          {index < sections.length - 1 ? <SectionDivider /> : null}
        </Fragment>
      ))}
    </DetailPageLayout>
  );
}

export function PortalDetailSection({
  children,
  intro,
  title,
}: PortalDetailSectionProps) {
  return (
    <SectionBlock intro={intro} title={title}>
      {children}
    </SectionBlock>
  );
}
