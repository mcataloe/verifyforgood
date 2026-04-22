import type { PropsWithChildren } from "react";

type PanelProps = PropsWithChildren<{
  subtitle?: string;
  title?: string;
}>;

export function Panel({ children, subtitle, title }: PanelProps) {
  return (
    <section className="shared-panel">
      {title || subtitle ? (
        <div className="shared-panel__header">
          {title ? <h3>{title}</h3> : null}
          {subtitle ? <p>{subtitle}</p> : null}
        </div>
      ) : null}
      <div className="shared-panel__content">{children}</div>
    </section>
  );
}
