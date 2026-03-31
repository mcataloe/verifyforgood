import type { HTMLAttributes } from "react";

interface SectionDividerProps extends HTMLAttributes<HTMLHRElement> {
  testId?: string;
}

export function SectionDivider({
  className,
  testId,
  ...rest
}: SectionDividerProps) {
  const resolvedClassName = className
    ? `portal-detail-layout__divider ${className}`
    : "portal-detail-layout__divider";

  return (
    <hr
      aria-hidden="true"
      className={resolvedClassName}
      data-testid={testId ?? "section-divider"}
      role="presentation"
      {...rest}
    />
  );
}
