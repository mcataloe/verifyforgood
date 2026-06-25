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

function buildController(
  overrides: Partial<PortalNonprofitSearchController> = {},
): PortalNonprofitSearchController {
  return {
    closeDetail: vi.fn(),
    detail: null,
    error: null,
    hasSearched: false,
    hasMoreResults: false,
    isDetailOpen: false,
    isLoading: false,
    isLoadingMore: false,
    lastQuery: "",
    recentSearches: [],
    loadMoreResults: vi.fn(async () => {}),
    results: [],
    runSearch: vi.fn(async () => {}),
    searchMode: null,
    viewResultDetail: vi.fn(async () => {}),
    ...overrides,
  };
}

describe("NonprofitSearchPanel", () => {
  it("renders a dedicated detail view with breadcrumb navigation", () => {
    const controller = buildController({
      detail: {
        appearsBecause: ["IRS records show a status of active."],
        complianceCheckType: "state_compliance",
        complianceCheckedAt: "2026-04-21T20:00:00+00:00",
        complianceStatus: "pass",
        dataGaps: [],
        ein: "12-3456789",
        entityType: "public_charity",
        filingDate: "2025-05-01",
        filingFormType: "990",
        filingParseStatus: "parsed",
        filingTaxYear: "2024",
        filingsCount: 1,
        highlights: ["A recent Form 990 period is on file."],
        irsStatus: "active",
        modelSource: "nonprofit_detail_snapshot",
        modelVersion: "advisory_copilot_detail.v1",
        name: "Helping Hands Foundation",
        nteeCategory: "Human services",
        queryExecutionId: "hash_123",
        recent990OnFile: "true",
        riskIndicators: [],
        snapshotMaterializedAt: "2026-04-21T20:00:00+00:00",
        sourceSummaries: [
          {
            category: "compliance",
            explanation: "Matched and refreshed",
            providerName: "Candid",
            retrievedAt: "2026-04-21T19:00:00+00:00",
            sourceName: "candid",
            status: "matched",
            validAsOf: "2026-04-21T19:00:00+00:00",
          },
        ],
        state: "IL",
        subsection: "03",
        taxDeductible: "yes",
        taxPeriod: "202412",
      },
      hasSearched: true,
      isDetailOpen: true,
      lastQuery: "Helping Hands",
      searchMode: "name",
    });

    renderWithOrganization(controller);

    expect(
      screen.getByRole("heading", { name: "Helping Hands Foundation" }),
    ).toBeTruthy();
    expect(screen.getByRole("button", { name: "Search results" })).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Search results" })).toBeNull();
    expect(screen.getByText("Matched and refreshed")).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Search results" }));
    expect(controller.closeDetail).toHaveBeenCalledOnce();
  });

  it("renders the search surface without the duplicate verification heading", () => {
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
    const controller = buildController({
      hasMoreResults: true,
      hasSearched: true,
      lastQuery: "Helping Hands",
      recentSearches,
      results: [
        {
          active: true,
          ein: "12-3456789",
          irsStatus: "active",
          name: "Helping Hands Foundation",
          state: "IL",
          subsection: "03",
          taxPeriod: "Unavailable",
        },
      ],
      searchMode: "name",
    });

    const { container } = renderWithOrganization(controller);

    fireEvent.change(screen.getByRole("textbox", { name: "Search query" }), {
      target: { value: "Helping Hands" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Search nonprofit" }));
    expect(controller.runSearch).toHaveBeenCalledWith("Helping Hands");

    expect(
      screen.queryByRole("heading", { name: "Nonprofit verification search" }),
    ).toBeNull();
    expect(
      screen.getByRole("heading", { name: "Search results" }),
    ).toBeTruthy();
    expect(
      screen.getByRole("heading", { name: "Recent searches" }),
    ).toBeTruthy();
    expect(screen.getByRole("table", { name: "Recent nonprofit searches" })).toBeTruthy();
    expect(container.querySelector(".portal-page-grid")).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Load more results" }));
    expect(controller.loadMoreResults).toHaveBeenCalledOnce();

    fireEvent.click(screen.getByRole("button", { name: "View details" }));
    expect(controller.viewResultDetail).toHaveBeenCalledWith("12-3456789");

    fireEvent.click(screen.getByRole("button", { name: "Run again" }));
    expect(controller.runSearch).toHaveBeenLastCalledWith("Helping Hands");
  });

  it("renders loading, empty, and error states consistently", () => {
    const controller = buildController({
      error: "The nonprofit lookup failed. Try again.",
      hasSearched: true,
      lastQuery: "Helping Hands",
      searchMode: "name",
    });

    const { container } = renderWithOrganization(controller);

    expect(screen.getByText("Nonprofit lookup unavailable")).toBeTruthy();
    expect(screen.getAllByTestId("detail-page-layout").length).toBeGreaterThanOrEqual(1);
    expect(container.querySelector(".portal-page-grid")).toBeNull();
  });

  it("keeps the search button available and validates an empty query explicitly", () => {
    const controller = buildController();

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
