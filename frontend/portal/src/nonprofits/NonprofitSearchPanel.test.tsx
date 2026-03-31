import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import { type PortalNonprofitSearchController } from "./usePortalNonprofitSearch";
import { NonprofitSearchPanel } from "./NonprofitSearchPanel";

function renderWithOrganization(controller: PortalNonprofitSearchController) {
  const value: PortalOrganizationContextValue = {
    activeOrganization: createSessionPortalOrganization({
      account_id: "acct_portal_test",
      auth_method: "mock_browser_session",
      organization_context_status: "active",
      organization_name: "Portal Test Org",
      workspace_id: "ws_portal_test",
    }),
    apiClient: {} as PortalOrganizationContextValue["apiClient"],
    currentMembership: {
      role: "admin",
      status: "active",
      user_id: "user_verifyforgood_demo",
    },
    isTenantReady: true,
    members: [],
    membersStatus: "ready",
    refresh: async () => {},
    refreshMembers: async () => [],
    selectionStatus: "active",
    setMembers: () => {},
    setActiveOrganization: () => {},
    status: "ready",
  };

  return render(
    <VerifyForGoodMantineProvider>
      <PortalOrganizationContext.Provider value={value}>
        <NonprofitSearchPanel controller={controller} />
      </PortalOrganizationContext.Provider>
    </VerifyForGoodMantineProvider>,
  );
}

describe("NonprofitSearchPanel", () => {
  it("renders summary results and detail data for nonprofit search", () => {
    const controller: PortalNonprofitSearchController = {
      detail: {
        ein: "12-3456789",
        entityType: "public_charity",
        filingDate: "2025-05-01",
        filingFormType: "990",
        filingParseStatus: "parsed",
        filingTaxYear: "2024",
        filingsCount: 1,
        irsStatus: "active",
        modelSource: "irs_eo_bmf_athena",
        modelVersion: "1.0.0",
        name: "Helping Hands Foundation",
        nteeCategory: "Human services",
        queryExecutionId: "qry_123",
        recent990OnFile: "true",
        state: "IL",
        sourceAvailability: [
          {
            attempted: false,
            integrationId: "candid",
            label: "Candid",
            status: "tenant_disabled",
          },
        ],
        subsection: "03",
        taxDeductible: "yes",
        taxPeriod: "202412",
      },
      error: null,
      hasSearched: true,
      hasMoreResults: true,
      isLoading: false,
      isLoadingMore: false,
      lastQuery: "Helping Hands",
      loadMoreResults: vi.fn(async () => {}),
      results: [
        {
          active: true,
          ein: "12-3456789",
          irsStatus: "active",
          name: "Helping Hands Foundation",
          state: "IL",
          subsection: "03",
          taxPeriod: "202412",
        },
      ],
      runSearch: vi.fn(async () => {}),
      searchMode: "name",
      viewResultDetail: vi.fn(async () => {}),
    };

    const { container } = renderWithOrganization(controller);

    fireEvent.change(screen.getByRole("textbox", { name: "Search query" }), {
      target: { value: "Helping Hands" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search nonprofit" }));
    expect(controller.runSearch).toHaveBeenCalledWith("Helping Hands");

    expect(screen.getAllByText("Helping Hands Foundation")).toHaveLength(2);
    expect(
      screen.getByRole("heading", { name: "Helping Hands Foundation" }),
    ).toBeTruthy();
    expect(screen.getByText("irs_eo_bmf_athena")).toBeTruthy();
    expect(screen.getByText("Disabled for this workspace")).toBeTruthy();
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(container.querySelector(".portal-page-grid")).toBeNull();
    expect(
      container.querySelectorAll(".portal-detail-layout__divider").length,
    ).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByRole("button", { name: "Load more results" }));
    expect(controller.loadMoreResults).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "View details" }));
    expect(controller.viewResultDetail).toHaveBeenCalledWith("12-3456789");
  });

  it("renders loading, empty, and error states consistently", () => {
    const controller: PortalNonprofitSearchController = {
      detail: null,
      error: "The nonprofit lookup failed. Try again.",
      hasSearched: true,
      hasMoreResults: false,
      isLoading: false,
      isLoadingMore: false,
      lastQuery: "Helping Hands",
      loadMoreResults: vi.fn(async () => {}),
      results: [],
      runSearch: vi.fn(async () => {}),
      searchMode: "name",
      viewResultDetail: vi.fn(async () => {}),
    };

    const { container } = renderWithOrganization(controller);

    expect(screen.getByText("Nonprofit lookup unavailable")).toBeTruthy();
    expect(container.querySelector(".portal-page-grid")).toBeNull();
  });
});
