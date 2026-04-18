import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import {
  PortalOrganizationContext,
  type PortalOrganizationContextValue,
} from "../organization/usePortalOrganization";
import { createSessionPortalOrganization } from "../organization/portalOrganization";
import {
  type PortalNonprofitSearchController,
  type PortalNonprofitSearchHistoryEntry,
} from "./usePortalNonprofitSearch";
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
    const recentSearches: PortalNonprofitSearchHistoryEntry[] = [
      {
        id: "search_1",
        outcome: "results_loaded",
        query: "Helping Hands",
        resultsCount: 1,
        searchMode: "name",
        searchedAt: "2026-04-18T18:40:00Z",
      },
    ];
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
        modelSource: "irs.eo_bmf",
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
      recentSearches,
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
    expect(screen.getAllByTestId("detail-page-layout").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Not enabled for your organization")).toBeTruthy();
    expect(screen.queryByText("irs.eo_bmf")).toBeNull();
    expect(screen.queryByText("ws_portal_test")).toBeNull();
    expect(screen.queryByRole("tablist")).toBeNull();
    expect(screen.queryByText("Search type")).toBeNull();
    expect(screen.queryByText("Results loaded")).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Recent searches" }),
    ).toBeTruthy();
    expect(screen.getByRole("table", { name: "Recent nonprofit searches" })).toBeTruthy();
    expect(container.querySelector(".portal-page-grid")).toBeNull();
    expect(
      screen.getAllByTestId("section-divider").length,
    ).toBeGreaterThanOrEqual(2);

    fireEvent.click(screen.getByRole("button", { name: "Load more results" }));
    expect(controller.loadMoreResults).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "View details" }));
    expect(controller.viewResultDetail).toHaveBeenCalledWith("12-3456789");

    fireEvent.click(screen.getByRole("button", { name: "Run again" }));
    expect(controller.runSearch).toHaveBeenLastCalledWith("Helping Hands");
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
      recentSearches: [],
      loadMoreResults: vi.fn(async () => {}),
      results: [],
      runSearch: vi.fn(async () => {}),
      searchMode: "name",
      viewResultDetail: vi.fn(async () => {}),
    };

    const { container } = renderWithOrganization(controller);

    expect(screen.getByText("Nonprofit lookup unavailable")).toBeTruthy();
    expect(screen.getAllByTestId("detail-page-layout").length).toBeGreaterThanOrEqual(1);
    expect(container.querySelector(".portal-page-grid")).toBeNull();
  });

  it("keeps the search button available and validates an empty query explicitly", () => {
    const controller: PortalNonprofitSearchController = {
      detail: null,
      error: null,
      hasSearched: false,
      hasMoreResults: false,
      isLoading: false,
      isLoadingMore: false,
      lastQuery: "",
      recentSearches: [],
      loadMoreResults: vi.fn(async () => {}),
      results: [],
      runSearch: vi.fn(async () => {}),
      searchMode: null,
      viewResultDetail: vi.fn(async () => {}),
    };

    renderWithOrganization(controller);

    const searchButton = screen.getByRole("button", {
      name: "Search nonprofit",
    }) as HTMLButtonElement;
    expect(searchButton.disabled).toBe(false);

    fireEvent.click(searchButton);
    expect(controller.runSearch).not.toHaveBeenCalled();
    expect(
      screen.getByText("Enter an EIN or organization name to search."),
    ).toBeTruthy();
  });
});
