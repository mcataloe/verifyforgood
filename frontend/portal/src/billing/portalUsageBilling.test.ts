import { describe, expect, it, vi } from "vitest";
import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import { createMockPortalSession } from "../app/portalSession";
import { createPortalUsageBillingService } from "./portalUsageBilling";

describe("portal usage billing service", () => {
  it("returns a mock snapshot for local demo sessions", async () => {
    const session = createMockPortalSession();
    const service = createPortalUsageBillingService({} as ApiClient);

    const snapshot = await service.loadSnapshot({
      organization: createSessionPortalOrganization({
        account_id: session.account_id,
        auth_method: session.auth_method,
        organization_name: session.organization_name,
        workspace_id: session.workspace_id,
      }),
      session,
    });

    expect(snapshot.source).toBe("session_mock");
    expect(snapshot.plan).toBe("growth");
    expect(snapshot.usage.limit).toBe(10000);
    expect(snapshot.budgetStatus.allowOverage).toBe(true);
  });

  it("loads backend subscription visibility for browser sessions", async () => {
    const session = {
      ...createMockPortalSession(),
      auth_method: "portal_browser_session" as const,
      billing_status: "active" as const,
      plan: "free",
    };
    const get = vi.fn(async (target: Parameters<ApiClient["get"]>[0]) => {
      expect(target).toBe(apiEndpoints.billing.subscription);
      return {
        billing_status: "active",
        effective_access_plan: "growth",
        pending_downgrade: {
          effective_at: "2026-04-01T00:00:00+00:00",
          plan: "starter",
        },
        plan: "pro",
        renewal_date: "2026-04-01T00:00:00+00:00",
        trial: {
          active: false,
          ends_at: null,
          status: null,
        },
      };
    });
    const service = createPortalUsageBillingService({
      get,
    } as unknown as ApiClient);

    const snapshot = await service.loadSnapshot({
      organization: {
        account_id: session.account_id,
        billing_allow_overage: false,
        organization_name: session.organization_name,
        scope_source: "backend_settings",
        settings_source: "stored",
        updated_at: null,
        workspace_id: session.workspace_id,
      },
      session,
    });

    expect(snapshot.source).toBe("backend_subscription");
    expect(snapshot.plan).toBe("pro");
    expect(snapshot.effectiveAccessPlan).toBe("growth");
    expect(snapshot.pendingDowngradePlan).toBe("starter");
    expect(snapshot.budgetStatus.allowOverage).toBe(false);
  });
});
