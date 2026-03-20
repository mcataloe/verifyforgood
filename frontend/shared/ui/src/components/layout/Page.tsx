import type { PropsWithChildren } from "react";

type PageProps = PropsWithChildren<{
  className?: string;
}>;

export function Page({ children, className }: PageProps) {
  const resolvedClassName = ["vf-page", className].filter(Boolean).join(" ");
  return <div className={resolvedClassName}>{children}</div>;
}
