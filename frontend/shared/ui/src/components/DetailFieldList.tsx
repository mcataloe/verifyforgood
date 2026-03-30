import type { ReactNode } from "react";

export type DetailFieldListItem = {
  detail?: ReactNode;
  key: string;
  label: ReactNode;
  value: ReactNode;
};

export function DetailFieldList({
  items,
  labelledBy,
}: {
  items: DetailFieldListItem[];
  labelledBy?: string;
}) {
  return (
    <dl aria-labelledby={labelledBy} className="vf-detail-field-list">
      {items.map((item) => (
        <div className="vf-detail-field-list__item" key={item.key}>
          <dt className="vf-detail-field-list__label">{item.label}</dt>
          <dd className="vf-detail-field-list__value">{item.value}</dd>
          {item.detail ? (
            <div className="vf-detail-field-list__detail">{item.detail}</div>
          ) : null}
        </div>
      ))}
    </dl>
  );
}
