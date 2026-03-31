import type { HTMLAttributes, PropsWithChildren, ReactNode } from "react";

interface DetailPageLayoutProps
  extends PropsWithChildren,
    Omit<HTMLAttributes<HTMLElement>, "title"> {
  eyebrow?: ReactNode;
  header?: ReactNode;
  intro?: ReactNode;
  className?: string;
  title?: ReactNode;
}

export function DetailPageLayout({
  children,
  className,
  eyebrow,
  header,
  intro,
  title,
  ...rest
}: DetailPageLayoutProps) {
  const resolvedClassName = className
    ? `portal-authenticated-container portal-detail-layout ${className}`
    : "portal-authenticated-container portal-detail-layout";

  return (
    <article
      className={resolvedClassName}
      data-testid="detail-page-layout"
      {...rest}
    >
      {header ? (
        header
      ) : title ? (
        <header className="portal-detail-layout__header">
          {eyebrow ? <p className="portal-shell__eyebrow">{eyebrow}</p> : null}
          <h1>{title}</h1>
          {intro ? <p className="portal-detail-layout__intro">{intro}</p> : null}
        </header>
      ) : null}
      <div className="portal-detail-layout__content">{children}</div>
    </article>
  );
}
