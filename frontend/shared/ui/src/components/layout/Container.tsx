import type { PropsWithChildren } from "react";

type ContainerProps = PropsWithChildren<{
  className?: string;
  size?: "content" | "full" | "narrow" | "wide";
}>;

export function Container({
  children,
  className,
  size = "content",
}: ContainerProps) {
  const resolvedClassName = ["vf-container", `vf-container--${size}`, className]
    .filter(Boolean)
    .join(" ");

  return <div className={resolvedClassName}>{children}</div>;
}
