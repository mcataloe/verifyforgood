import type { FrontendAccessRole, PlanCode } from "@charity-status/shared-types";
import type { ReactNode } from "react";

export type VerifyForGoodNavigationVisibilityState =
  | "hidden"
  | "locked"
  | "visible";

export type VerifyForGoodRestrictedVisibility = Extract<
  VerifyForGoodNavigationVisibilityState,
  "hidden" | "locked"
>;

export interface VerifyForGoodNavigationVisibility {
  /** How plan-restricted items resolve when the active plan does not qualify. */
  planRestrictedBehavior?: VerifyForGoodRestrictedVisibility;
  /** How role-restricted items resolve when the active role set does not qualify. */
  roleRestrictedBehavior?: VerifyForGoodRestrictedVisibility;
}

export interface VerifyForGoodNavigationItem {
  key: string;
  /** Short visible title used in the rendered navigation UI. */
  label: string;
  /** Optional longer tooltip/help copy that supplements the visible label. */
  helpText?: string;
  href?: string;
  icon?: ReactNode;
  children?: VerifyForGoodNavigationItem[];
  allowedPlans?: readonly PlanCode[];
  allowedRoles?: readonly FrontendAccessRole[];
  visibility?: VerifyForGoodNavigationVisibility;
}

export interface VerifyForGoodNavigationSection {
  key: string;
  /** Short visible section title used in the rendered navigation UI. */
  label: string;
  /** Optional longer tooltip/help copy that supplements the section title. */
  helpText?: string;
  items: VerifyForGoodNavigationItem[];
}

export interface VerifyForGoodResolvedNavigationItem
  extends Omit<VerifyForGoodNavigationItem, "children"> {
  children?: VerifyForGoodResolvedNavigationItem[];
  /** Final render state after role/plan filtering has been applied upstream. */
  visibilityState: Exclude<VerifyForGoodNavigationVisibilityState, "hidden">;
}

export interface VerifyForGoodResolvedNavigationSection
  extends Omit<VerifyForGoodNavigationSection, "items"> {
  items: VerifyForGoodResolvedNavigationItem[];
}

export interface VerifyForGoodNavigationAccessContext {
  plan: string;
  roles: readonly FrontendAccessRole[];
}
