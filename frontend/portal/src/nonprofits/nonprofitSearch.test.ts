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

  it("runs exact EIN lookup and merges filing details", async () => {
    const get = vi.fn(
      async (
        target: Parameters<ApiClient["get"]>[0],
        options?: Parameters<ApiClient["get"]>[1],
      ) => {
        if (target === apiEndpoints.nonprofits.lookup) {
          expect(options?.pathParams).toEqual({
            ein: "123456789",
          });
          return {
            filing_summary: {
              filing_date: "2025-05-01",
              form_type: "990",
              parse_status: "parsed",
              tax_year: "2024",
            },
            model: {
              source: "irs_eo_bmf_athena",
              version: "1.0.0",
            },
            organization: {
              ein: "12-3456789",
              name: "Helping Hands Foundation",
            },
            queryExecutionId: "qry_123",
            source_record: {
              subsection: "03",
              tax_period: "202412",
            },
            verification: {
              entity_type: "public_charity",
              irs_status: "active",
              ntee_category: "Human services",
              recent_990_on_file: true,
              state: "IL",
              tax_deductible: "yes",
            },
          };
        }

        return {
          ein: "123456789",
          filings: [
            {
              filing_date: "2025-05-01",
              form_type: "990",
              parse_status: "parsed",
              tax_year: "2024",
            },
          ],
        };
      },
    );
    const service = createPortalNonprofitSearchService({
      get,
    } as unknown as ApiClient);

    const detail = await service.lookupByEin("12-3456789");

    expect(detail?.name).toBe("Helping Hands Foundation");
    expect(detail?.filingTaxYear).toBe("2024");
    expect(detail?.filingsCount).toBe(1);
    expect(detail?.modelSource).toBe("irs_eo_bmf_athena");
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

    expect(results).toEqual([
      {
        active: true,
        ein: "12-3456789",
        irsStatus: "active",
        name: "Helping Hands Foundation",
        state: "IL",
        subsection: "03",
        taxPeriod: "202412",
      },
    ]);
  });
});
