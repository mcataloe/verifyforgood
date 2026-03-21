import type { CSSProperties, PropsWithChildren } from "react";

type GridProps = PropsWithChildren<{
  className?: string;
  gap?: string;
  minItemWidth?: string;
}>;

export function Grid({ children, className, gap, minItemWidth }: GridProps) {
  const resolvedClassName = ["vf-grid", className].filter(Boolean).join(" ");
  const style = {
    "--vf-grid-gap": gap,
    "--vf-grid-min": minItemWidth,
  } as CSSProperties;

  return (
    <div className={resolvedClassName} style={style}>
      {children}
    </div>
  );
}
