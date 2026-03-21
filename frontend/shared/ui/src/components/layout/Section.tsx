import type { PropsWithChildren } from "react";

type SectionProps = PropsWithChildren<{
  className?: string;
}>;

export function Section({ children, className }: SectionProps) {
  const resolvedClassName = ["vf-section", className].filter(Boolean).join(" ");
  return <section className={resolvedClassName}>{children}</section>;
}
