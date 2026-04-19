import { PageHeader } from "@charity-status/shared-ui";
import { Stack } from "@mantine/core";
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
  eyebrow,
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
          <PageHeader eyebrow={eyebrow} description={intro} title={title} />
        </header>
      ) : null}
      <Stack
        className="portal-detail-layout__content"
        data-testid={contentTestId ?? "detail-page-layout-content"}
        gap="xl"
      >
        {children}
      </Stack>
    </article>
  );
}
