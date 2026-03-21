import type { PropsWithChildren, ReactNode } from "react";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { PlanFeatureList } from "./PlanFeatureList";

export interface PricingPlanCardProps extends PropsWithChildren {
  cta?: ReactNode;
  footnote?: ReactNode;
  highlighted?: boolean;
  isCurrent?: boolean;
  isEffective?: boolean;
  isPending?: boolean;
  plan: PricingPlanMetadata;
}

export function PricingPlanCard({
  children,
  cta,
  footnote,
  highlighted = false,
  isCurrent = false,
  isEffective = false,
  isPending = false,
  plan,
}: PricingPlanCardProps) {
  const badges = [
    isCurrent ? "Current billing plan" : null,
    isEffective ? "Effective access" : null,
    isPending ? "Pending downgrade" : null,
  ].filter(Boolean);

  return (
    <article
      className={
        highlighted
          ? "pricing-plan-card pricing-plan-card--highlighted"
          : "pricing-plan-card"
      }
    >
      <div className="pricing-plan-card__header">
        <div>
          <p className="pricing-plan-card__eyebrow">{plan.plan_code}</p>
          <h3>{plan.display_name}</h3>
        </div>
        {badges.length > 0 ? (
          <div className="pricing-plan-card__badges">
            {badges.map((badge) => (
              <span key={badge} className="pricing-plan-card__badge">
                {badge}
              </span>
            ))}
          </div>
        ) : null}
      </div>

      <dl className="pricing-plan-card__usage">
        <div>
          <dt>Monthly requests</dt>
          <dd>{plan.included_usage.monthly_requests.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Batch items</dt>
          <dd>{plan.included_usage.batch_items.toLocaleString()}</dd>
        </div>
        <div>
          <dt>Requests per minute</dt>
          <dd>{plan.included_usage.requests_per_minute.toLocaleString()}</dd>
        </div>
      </dl>

      <p className="pricing-plan-card__pricing">
        Overage pricing:{" "}
        <strong>
          {formatUsdMicros(plan.per_request_pricing.amount_usd_micros)}
        </strong>{" "}
        per {plan.per_request_pricing.unit}.
      </p>

      <PlanFeatureList featureAvailability={plan.feature_availability} />

      {children ? (
        <div className="pricing-plan-card__content">{children}</div>
      ) : null}
      {cta ? <div className="pricing-plan-card__cta">{cta}</div> : null}
      {footnote ? (
        <div className="pricing-plan-card__footnote">{footnote}</div>
      ) : null}
    </article>
  );
}

function formatUsdMicros(amountUsdMicros: number): string {
  return new Intl.NumberFormat("en-US", {
    currency: "USD",
    maximumFractionDigits: 3,
    minimumFractionDigits: 3,
    style: "currency",
  }).format(amountUsdMicros / 1_000_000);
}
