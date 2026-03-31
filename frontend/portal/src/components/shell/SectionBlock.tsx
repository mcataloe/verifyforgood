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
      {title || intro ? (
        <div className="portal-detail-layout__section-header">
          {title ? <h2>{title}</h2> : null}
          {intro ? (
            <p className="portal-detail-layout__section-intro">{intro}</p>
          ) : null}
        </div>
      ) : null}
      <div className="portal-detail-layout__section-body">{children}</div>
    </section>
  );
}
