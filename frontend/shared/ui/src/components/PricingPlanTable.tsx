import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { FEATURE_LABELS, FEATURE_ORDER } from "./PlanFeatureList";

export interface PricingPlanTableProps {
  plans: PricingPlanMetadata[];
}

export function PricingPlanTable({ plans }: PricingPlanTableProps) {
  return (
    <div className="pricing-plan-table-wrap">
      <table className="pricing-plan-table">
        <caption className="pricing-plan-table__caption">
          Compare plan features, cost, and API limits to choose the right
          plan for your organization.
        </caption>
        <thead>
          <tr>
            <th scope="col">Plan</th>
            {plans.map((plan) => (
              <th key={plan.plan_code} scope="col">
                {plan.display_name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Monthly requests</th>
            {plans.map((plan) => (
              <td key={plan.plan_code}>
                {plan.included_usage.monthly_requests.toLocaleString()}
              </td>
            ))}
          </tr>
          <tr>
            <th scope="row">Batch items</th>
            {plans.map((plan) => (
              <td key={plan.plan_code}>
                {plan.included_usage.batch_items.toLocaleString()}
              </td>
            ))}
          </tr>
          <tr>
            <th scope="row">Requests per minute</th>
            {plans.map((plan) => (
              <td key={plan.plan_code}>
                {plan.included_usage.requests_per_minute.toLocaleString()}
              </td>
            ))}
          </tr>
          <tr>
            <th scope="row">Overage pricing</th>
            {plans.map((plan) => (
              <td key={plan.plan_code}>
                {formatUsdMicros(plan.per_request_pricing.amount_usd_micros)}
                {" "}
                per {plan.per_request_pricing.unit}
              </td>
            ))}
          </tr>
          {FEATURE_ORDER.map((featureKey) => (
            <tr key={featureKey}>
              <th scope="row">{FEATURE_LABELS[featureKey]}</th>
              {plans.map((plan) => {
                const available = plan.feature_availability[featureKey];
                return (
                  <td key={plan.plan_code}>
                    <span
                      className={
                        available
                          ? "pricing-plan-table__pill pricing-plan-table__pill--available"
                          : "pricing-plan-table__pill pricing-plan-table__pill--unavailable"
                      }
                    >
                      {available ? "Included" : "Not included"}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
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
