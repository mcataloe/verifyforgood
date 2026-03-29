import type { ReactNode } from "react";
import type { PricingPlanMetadata } from "@charity-status/shared-types";
import { PricingPlanCard } from "./PricingPlanCard";

export interface PricingPlanGridItem {
  cta?: ReactNode;
  footnote?: ReactNode;
  highlighted?: boolean;
  isCurrent?: boolean;
  isEffective?: boolean;
  isPending?: boolean;
  pendingLabel?: string;
  plan: PricingPlanMetadata;
}

interface PricingPlanGridProps {
  items: PricingPlanGridItem[];
}

export function PricingPlanGrid({ items }: PricingPlanGridProps) {
  return (
    <div className="pricing-plan-grid">
      {items.map((item) => (
        <PricingPlanCard
          key={item.plan.plan_code}
          cta={item.cta}
          footnote={item.footnote}
          highlighted={item.highlighted}
          isCurrent={item.isCurrent}
          isEffective={item.isEffective}
          isPending={item.isPending}
          pendingLabel={item.pendingLabel}
          plan={item.plan}
        />
      ))}
    </div>
  );
}
