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
  planRestrictedBehavior?: VerifyForGoodRestrictedVisibility;
  roleRestrictedBehavior?: VerifyForGoodRestrictedVisibility;
}

export interface VerifyForGoodNavigationItem {
  key: string;
  label: string;
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
  label: string;
  helpText?: string;
  items: VerifyForGoodNavigationItem[];
}

export interface VerifyForGoodResolvedNavigationItem
  extends Omit<VerifyForGoodNavigationItem, "children"> {
  children?: VerifyForGoodResolvedNavigationItem[];
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
