import { SectionContainer } from "@charity-status/shared-ui";
import type { PropsWithChildren, ReactNode } from "react";

interface SectionBlockProps extends PropsWithChildren {
  className?: string;
  intro?: ReactNode;
  title?: ReactNode;
}

export function SectionBlock({
  children,
  className,
  intro,
  title,
}: SectionBlockProps) {
  const resolvedClassName = className
    ? `portal-detail-layout__section ${className}`
    : "portal-detail-layout__section";

  return (
    <section className={resolvedClassName}>
      <SectionContainer description={intro} gap="md" title={title}>
        <div className="portal-detail-layout__section-body">{children}</div>
      </SectionContainer>
    </section>
  );
}
