import type {
  PlanFeatureAvailability,
  PlanFeatureKey,
} from "@charity-status/shared-types";

export const FEATURE_ORDER: PlanFeatureKey[] = [
  "verification",
  "risk_flags",
  "financial_trends",
  "benchmarking",
  "state_registry",
  "monitoring",
  "batch_verification",
  "organization_settings",
];

export const FEATURE_LABELS: Record<PlanFeatureKey, string> = {
  verification: "Verification",
  risk_flags: "Risk flags",
  financial_trends: "Financial trends",
  benchmarking: "Benchmarking",
  state_registry: "State registry",
  monitoring: "Monitoring",
  batch_verification: "Batch verification",
  organization_settings: "Organization settings",
};

interface PlanFeatureListProps {
  featureAvailability: PlanFeatureAvailability;
}

export function PlanFeatureList({ featureAvailability }: PlanFeatureListProps) {
  return (
    <ul className="pricing-plan-feature-list">
      {FEATURE_ORDER.map((featureKey) => {
        const available = featureAvailability[featureKey];
        return (
          <li
            key={featureKey}
            className={
              available
                ? "pricing-plan-feature-list__item pricing-plan-feature-list__item--available"
                : "pricing-plan-feature-list__item pricing-plan-feature-list__item--unavailable"
            }
          >
            <span aria-hidden="true">
              {available ? "Included" : "Not included"}
            </span>
            <span>{FEATURE_LABELS[featureKey]}</span>
          </li>
        );
      })}
    </ul>
  );
}
