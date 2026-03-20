import type { CSSProperties, PropsWithChildren } from "react";

type InlineProps = PropsWithChildren<{
  align?: string;
  className?: string;
  gap?: string;
}>;

export function Inline({
  align,
  children,
  className,
  gap,
}: InlineProps) {
  const resolvedClassName = ["vf-inline", className].filter(Boolean).join(" ");
  const style = {
    "--vf-inline-align": align,
    "--vf-inline-gap": gap,
  } as CSSProperties;

  return (
    <div className={resolvedClassName} style={style}>
      {children}
    </div>
  );
}
