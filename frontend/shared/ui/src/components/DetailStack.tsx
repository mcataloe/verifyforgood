import type { PropsWithChildren, ReactNode } from "react";

export function DetailStack({
  children,
  description,
  title,
}: PropsWithChildren<{
  description?: ReactNode;
  title?: ReactNode;
}>) {
  return (
    <div className="vf-detail-stack">
      {title || description ? (
        <div className="vf-detail-stack__header">
          {title ? <h3 className="vf-detail-stack__title">{title}</h3> : null}
          {description ? (
            <p className="vf-detail-stack__description">{description}</p>
          ) : null}
        </div>
      ) : null}
      <div className="vf-detail-stack__body">{children}</div>
    </div>
  );
}
