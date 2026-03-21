import type { PropsWithChildren } from "react";

type ThemeRootProps = PropsWithChildren<{
  className?: string;
  tone?: "default" | "inverse";
}>;

export function ThemeRoot({
  children,
  className,
  tone = "default",
}: ThemeRootProps) {
  const resolvedClassName = ["vf-theme-root", className]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={resolvedClassName} data-theme={tone}>
      {children}
    </div>
  );
}
