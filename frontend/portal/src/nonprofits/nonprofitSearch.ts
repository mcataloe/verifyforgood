import {
  ApiRequestError,
  apiEndpoints,
  type ApiClient,
} from "@charity-status/shared-api";

interface BackendNonprofitLookupResponse {
  filing_summary?: {
    amended?: boolean | null;
    filing_date?: string | null;
    form_type?: string | null;
    parse_status?: string | null;
    tax_year?: string | null;
  };
  model?: {
    source?: string | null;
    version?: string | null;
  };
  organization?: {
    ein?: string | null;
    name?: string | null;
  };
  queryExecutionId?: string | null;
  source_record?: {
    subsection?: string | null;
    tax_period?: string | null;
  };
  verification?: {
    entity_type?: string | null;
    irs_status?: string | null;
    ntee_category?: string | null;
    recent_990_on_file?: boolean | null;
    state?: string | null;
    tax_deductible?: string | boolean | null;
  };
}

interface BackendNonprofitFilingsResponse {
  ein?: string | null;
  filings?: Array<{
    amended?: boolean | null;
    filing_date?: string | null;
    form_type?: string | null;
    parse_status?: string | null;
    tax_year?: string | null;
  }>;
}

interface BackendNonprofitSearchResponse {
  items?: Array<{
    active?: boolean | null;
    ein?: string | null;
    ein_normalized?: string | null;
    irs_status?: string | null;
    name?: string | null;
    state?: string | null;
    subsection?: string | null;
    tax_period?: string | null;
  }>;
  pagination?: {
    limit?: number | null;
    next_cursor?: string | null;
  };
  query?: string | null;
}

export interface PortalNonprofitSearchSummary {
  active: boolean | null;
  ein: string;
  irsStatus: string;
  name: string;
  state: string;
  subsection: string;
  taxPeriod: string;
}

export interface PortalNonprofitDetail {
  ein: string;
  entityType: string;
  filingDate: string;
  filingFormType: string;
  filingParseStatus: string;
  filingTaxYear: string;
  filingsCount: number;
  irsStatus: string;
  modelSource: string;
  modelVersion: string;
  name: string;
  nteeCategory: string;
  queryExecutionId: string;
  recent990OnFile: string;
  state: string;
  subsection: string;
  taxDeductible: string;
  taxPeriod: string;
}

export interface PortalNonprofitSearchService {
  lookupByEin(ein: string): Promise<PortalNonprofitDetail | null>;
  searchByName(query: string): Promise<PortalNonprofitSearchSummary[]>;
}

export function createPortalNonprofitSearchService(
  apiClient: ApiClient,
): PortalNonprofitSearchService {
  return {
    async lookupByEin(ein) {
      const normalizedEin = normalizeEinQuery(ein);
      if (!normalizedEin) {
        return null;
      }

      try {
        const [lookupResult, filingsResult] = await Promise.allSettled([
          apiClient.get<BackendNonprofitLookupResponse>(
            apiEndpoints.nonprofits.lookup,
            {
              pathParams: {
                ein: normalizedEin,
              },
            },
          ),
          apiClient.get<BackendNonprofitFilingsResponse>(
            apiEndpoints.nonprofits.filings,
            {
              pathParams: {
                ein: normalizedEin,
              },
            },
          ),
        ]);

        if (lookupResult.status === "rejected") {
          throw lookupResult.reason;
        }

        const filings =
          filingsResult.status === "fulfilled"
            ? (filingsResult.value.filings ?? [])
            : [];

        return mapLookupDetail(lookupResult.value, filings);
      } catch (error) {
        if (error instanceof ApiRequestError && error.status === 404) {
          return null;
        }

        throw error;
      }
    },
    async searchByName(query) {
      const trimmedQuery = query.trim();
      if (!trimmedQuery) {
        return [];
      }

      const response = await apiClient.get<BackendNonprofitSearchResponse>(
        apiEndpoints.nonprofits.search,
        {
          query: {
            limit: 8,
            q: trimmedQuery,
          },
        },
      );

      return (response.items ?? []).map(mapSearchSummary);
    },
  };
}

export function looksLikeEinQuery(query: string): boolean {
  return normalizeEinQuery(query) !== null;
}

export function normalizeEinQuery(query: string): string | null {
  const digitsOnly = String(query || "").replaceAll(/\D/g, "");
  return digitsOnly.length === 9 ? digitsOnly : null;
}

function mapLookupDetail(
  lookup: BackendNonprofitLookupResponse,
  filings: BackendNonprofitFilingsResponse["filings"] = [],
): PortalNonprofitDetail {
  const filingSummary = lookup.filing_summary ?? filings[0] ?? null;

  return {
    ein: normalizeText(lookup.organization?.ein, "Unavailable"),
    entityType: normalizeText(lookup.verification?.entity_type, "Unavailable"),
    filingDate: normalizeText(filingSummary?.filing_date, "No filing date"),
    filingFormType: normalizeText(filingSummary?.form_type, "No filing form"),
    filingParseStatus: normalizeText(
      filingSummary?.parse_status,
      "No filing parse status",
    ),
    filingTaxYear: normalizeText(filingSummary?.tax_year, "No filing year"),
    filingsCount: filings.length,
    irsStatus: normalizeText(lookup.verification?.irs_status, "Unavailable"),
    modelSource: normalizeText(lookup.model?.source, "Unavailable"),
    modelVersion: normalizeText(lookup.model?.version, "Unavailable"),
    name: normalizeText(lookup.organization?.name, "Unknown organization"),
    nteeCategory: normalizeText(
      lookup.verification?.ntee_category,
      "Unavailable",
    ),
    queryExecutionId: normalizeText(
      lookup.queryExecutionId,
      "No query execution id",
    ),
    recent990OnFile:
      typeof lookup.verification?.recent_990_on_file === "boolean"
        ? String(lookup.verification.recent_990_on_file)
        : "Unknown",
    state: normalizeText(lookup.verification?.state, "Unavailable"),
    subsection: normalizeText(lookup.source_record?.subsection, "Unavailable"),
    taxDeductible: normalizeText(
      lookup.verification?.tax_deductible,
      "Unavailable",
    ),
    taxPeriod: normalizeText(lookup.source_record?.tax_period, "Unavailable"),
  };
}

function mapSearchSummary(
  item: NonNullable<BackendNonprofitSearchResponse["items"]>[number],
): PortalNonprofitSearchSummary {
  return {
    active: typeof item.active === "boolean" ? item.active : null,
    ein: normalizeText(
      item.ein,
      normalizeText(item.ein_normalized, "Unknown EIN"),
    ),
    irsStatus: normalizeText(item.irs_status, "Unavailable"),
    name: normalizeText(item.name, "Unknown organization"),
    state: normalizeText(item.state, "Unavailable"),
    subsection: normalizeText(item.subsection, "Unavailable"),
    taxPeriod: normalizeText(item.tax_period, "Unavailable"),
  };
}

function normalizeText(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "boolean") {
    return String(value);
  }

  return fallback;
}
