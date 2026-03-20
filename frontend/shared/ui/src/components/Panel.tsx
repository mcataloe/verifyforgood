import type { PropsWithChildren } from "react";

type PanelProps = PropsWithChildren<{
  subtitle?: string;
  title: string;
}>;

export function Panel({ children, subtitle, title }: PanelProps) {
  return (
    <section className="shared-panel">
      <div className="shared-panel__header">
        <h3>{title}</h3>
        {subtitle ? <p>{subtitle}</p> : null}
      </div>
      <div className="shared-panel__content">{children}</div>
    </section>
  );
}
