import { describe, expect, it, vi } from "vitest";
import { apiEndpoints, type ApiClient } from "@charity-status/shared-api";
import {
  createPortalNonprofitSearchService,
  looksLikeEinQuery,
  normalizeEinQuery,
} from "./nonprofitSearch";

describe("portal nonprofit search service", () => {
  it("normalizes EIN input and detects EIN searches", () => {
    expect(normalizeEinQuery("12-3456789")).toBe("123456789");
    expect(looksLikeEinQuery("12-3456789")).toBe(true);
    expect(looksLikeEinQuery("Helping Hands")).toBe(false);
  });

  it("runs exact EIN lookup against the advisory detail endpoint", async () => {
    const get = vi.fn(
      async (
        target: Parameters<ApiClient["get"]>[0],
        options?: Parameters<ApiClient["get"]>[1],
      ) => {
        if (target === apiEndpoints.nonprofits.detail) {
          expect(options?.pathParams).toEqual({
            ein: "123456789",
          });
          return {
            filings: {
              count: 1,
              latest: {
                filing_date: "2025-05-01",
                parse_status: "parsed",
                return_type: "990",
                tax_period: "202412",
                tax_year: "2024",
              },
              recent_990_on_file: true,
            },
            organization: {
              ein: "12-3456789",
              name: "Helping Hands Foundation",
            },
            overview: {
              entity_type: "public_charity",
              irs_status: "active",
              ntee_category: "Human services",
              state: "IL",
              subsection: "03",
              tax_deductible: "yes",
            },
            signals: {
              appears_because: ["IRS records show a status of active."],
              data_gaps: ["No compliance snapshot is available yet."],
              highlights: ["A recent Form 990 period is on file."],
              risk_indicators: [],
            },
            snapshot: {
              materialized_at: "2026-04-21T20:00:00+00:00",
              renderer_version: "advisory_copilot_detail.v1",
              schema_version: "nonprofit_detail_snapshot.v1",
              source_hash: "hash_123",
            },
            sources: [
              {
                category: "compliance",
                explanation: "Matched and refreshed",
                provider_name: "Candid",
                retrieved_at: "2026-04-21T19:00:00+00:00",
                source_name: "candid",
                status: "matched",
                valid_as_of: "2026-04-21T19:00:00+00:00",
              },
            ],
          };
        }

        throw new Error(`Unexpected endpoint ${String(target)}`);
      },
    );
    const service = createPortalNonprofitSearchService({
      get,
    } as unknown as ApiClient);

    const detail = await service.lookupByEin("12-3456789");

    expect(detail?.name).toBe("Helping Hands Foundation");
    expect(detail?.filingTaxYear).toBe("2024");
    expect(detail?.filingsCount).toBe(1);
    expect(detail?.modelSource).toBe("nonprofit_detail_snapshot");
    expect(detail?.appearsBecause).toEqual([
      "IRS records show a status of active.",
    ]);
    expect(detail?.sourceSummaries).toEqual([
      {
        category: "compliance",
        explanation: "Matched and refreshed",
        providerName: "Candid",
        retrievedAt: "2026-04-21T19:00:00+00:00",
        sourceName: "candid",
        status: "matched",
        validAsOf: "2026-04-21T19:00:00+00:00",
      },
    ]);
  });

  it("runs name search and maps lightweight nonprofit summaries", async () => {
    const get = vi.fn(
      async (
        target: Parameters<ApiClient["get"]>[0],
        options?: Parameters<ApiClient["get"]>[1],
      ) => {
        expect(target).toBe(apiEndpoints.nonprofits.search);
        expect(options?.query).toEqual({
          limit: 8,
          q: "Helping Hands",
        });
        return {
          items: [
            {
              active: true,
              ein: "12-3456789",
              irs_status: "active",
              name: "Helping Hands Foundation",
              state: "IL",
              subsection: "03",
              tax_period: "202412",
            },
          ],
        };
      },
    );
    const service = createPortalNonprofitSearchService({
      get,
    } as unknown as ApiClient);

    const results = await service.searchByName("Helping Hands");

    expect(results).toEqual({
      items: [
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
      nextCursor: null,
    });
  });

  it("passes the backend cursor through for paginated name search", async () => {
    const get = vi.fn(
      async (
        target: Parameters<ApiClient["get"]>[0],
        options?: Parameters<ApiClient["get"]>[1],
      ) => {
        expect(target).toBe(apiEndpoints.nonprofits.search);
        expect(options?.query).toEqual({
          cursor: "cursor_123",
          limit: 5,
          q: "Helping Hands",
        });
        return {
          items: [],
          pagination: {
            next_cursor: "cursor_456",
          },
        };
      },
    );
    const service = createPortalNonprofitSearchService({
      get,
    } as unknown as ApiClient);

    const results = await service.searchByName("Helping Hands", {
      cursor: "cursor_123",
      limit: 5,
    });

    expect(results).toEqual({
      items: [],
      nextCursor: "cursor_456",
    });
  });
});
