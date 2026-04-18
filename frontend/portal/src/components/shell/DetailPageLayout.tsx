import type { HTMLAttributes, PropsWithChildren, ReactNode } from "react";

interface DetailPageLayoutProps
  extends PropsWithChildren,
    Omit<HTMLAttributes<HTMLElement>, "title"> {
  eyebrow?: ReactNode;
  header?: ReactNode;
  intro?: ReactNode;
  className?: string;
  contentTestId?: string;
  testId?: string;
  title?: ReactNode;
}

export function DetailPageLayout({
  children,
  className,
  contentTestId,
  header,
  intro,
  testId,
  title,
  ...rest
}: DetailPageLayoutProps) {
  const resolvedClassName = className
    ? `portal-authenticated-container portal-detail-layout ${className}`
    : "portal-authenticated-container portal-detail-layout";

  return (
    <article
      className={resolvedClassName}
      data-testid={testId ?? "detail-page-layout"}
      {...rest}
    >
      {header ? (
        header
      ) : title ? (
        <header className="portal-detail-layout__header">
          <h1>{title}</h1>
          {intro ? <p className="portal-detail-layout__intro">{intro}</p> : null}
        </header>
      ) : null}
      <div
        className="portal-detail-layout__content"
        data-testid={contentTestId ?? "detail-page-layout-content"}
      >
        {children}
      </div>
    </article>
  );
}
