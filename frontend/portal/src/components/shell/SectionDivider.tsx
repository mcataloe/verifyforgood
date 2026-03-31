import type { HTMLAttributes } from "react";

export function SectionDivider({
  className,
  ...rest
}: HTMLAttributes<HTMLHRElement>) {
  const resolvedClassName = className
    ? `portal-detail-layout__divider ${className}`
    : "portal-detail-layout__divider";

  return <hr aria-hidden="true" className={resolvedClassName} role="presentation" {...rest} />;
}
