import { hasAnyRole } from "@charity-status/shared-utils";
import type {
  VerifyForGoodNavigationAccessContext,
  VerifyForGoodNavigationItem,
  VerifyForGoodNavigationSection,
  VerifyForGoodNavigationVisibility,
  VerifyForGoodNavigationVisibilityState,
  VerifyForGoodResolvedNavigationItem,
  VerifyForGoodResolvedNavigationSection,
} from "./schema";

const DEFAULT_VISIBILITY: Required<VerifyForGoodNavigationVisibility> = {
  planRestrictedBehavior: "locked",
  roleRestrictedBehavior: "hidden",
};

export function filterNavigationSections(
  sections: readonly VerifyForGoodNavigationSection[],
  access: VerifyForGoodNavigationAccessContext,
): VerifyForGoodResolvedNavigationSection[] {
  return sections
    .map((section) => ({
      ...section,
      items: section.items.flatMap((item) => {
        const resolvedItem = resolveNavigationItem(item, access);
        return resolvedItem ? [resolvedItem] : [];
      }),
    }))
    .filter((section) => section.items.length > 0);
}

export function resolveNavigationItem(
  item: VerifyForGoodNavigationItem,
  access: VerifyForGoodNavigationAccessContext,
): VerifyForGoodResolvedNavigationItem | null {
  const directVisibility = resolveDirectVisibility(item, access);
  const resolvedChildren =
    item.children?.flatMap((child) => {
      const resolvedChild = resolveNavigationItem(child, access);
      return resolvedChild ? [resolvedChild] : [];
    }) ?? [];

  if (directVisibility === "hidden" && resolvedChildren.length === 0) {
    return null;
  }

  if (resolvedChildren.length > 0) {
    return {
      ...item,
      children: resolvedChildren,
      href: undefined,
      visibilityState: "visible",
    };
  }

  if (directVisibility === "hidden") {
    return null;
  }

  return {
    ...item,
    children: resolvedChildren.length > 0 ? resolvedChildren : undefined,
    href: directVisibility === "locked" ? undefined : item.href,
    visibilityState: directVisibility,
  };
}

function resolveDirectVisibility(
  item: VerifyForGoodNavigationItem,
  access: VerifyForGoodNavigationAccessContext,
): VerifyForGoodNavigationVisibilityState {
  const visibility = {
    ...DEFAULT_VISIBILITY,
    ...item.visibility,
  };

  if (item.allowedRoles && !hasAnyRole(access.roles, item.allowedRoles)) {
    return visibility.roleRestrictedBehavior;
  }

  if (item.allowedPlans && !item.allowedPlans.includes(access.plan as never)) {
    return visibility.planRestrictedBehavior;
  }

  return "visible";
}
