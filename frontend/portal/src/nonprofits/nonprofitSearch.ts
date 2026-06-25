import {
  ApiRequestError,
  apiEndpoints,
  type ApiClient,
} from "@charity-status/shared-api";

interface BackendNonprofitDetailResponse {
  compliance?: {
    check_type?: string | null;
    evaluated_at?: string | null;
    reasons?: unknown;
    status?: string | null;
    summary?: unknown;
  };
  filings?: {
    count?: number | null;
    latest?: {
      amended_return?: boolean | null;
      filing_date?: string | null;
      parse_status?: string | null;
      return_type?: string | null;
      tax_period?: string | null;
      tax_year?: string | number | null;
    } | null;
    recent_990_on_file?: boolean | null;
  };
  organization?: {
    ein?: string | null;
    name?: string | null;
  };
  overview?: {
    canonical_source?: string | null;
    entity_type?: string | null;
    irs_status?: string | null;
    ntee_category?: string | null;
    source_version?: string | null;
    state?: string | null;
    subsection?: string | null;
    tax_deductible?: string | boolean | null;
  };
  signals?: {
    appears_because?: unknown;
    data_gaps?: unknown;
    highlights?: unknown;
    risk_indicators?: unknown;
  };
  snapshot?: {
    materialized_at?: string | null;
    renderer_version?: string | null;
    schema_version?: string | null;
    source_hash?: string | null;
  };
  sources?: Array<{
    category?: string | null;
    explanation?: string | null;
    provider_name?: string | null;
    retrieved_at?: string | null;
    source_name?: string | null;
    status?: string | null;
    valid_as_of?: string | null;
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

export interface PortalNonprofitSourceSummary {
  category: string;
  explanation: string;
  providerName: string;
  retrievedAt: string;
  sourceName: string;
  status: string;
  validAsOf: string;
}

export interface PortalNonprofitDetail {
  appearsBecause: string[];
  complianceCheckType: string;
  complianceCheckedAt: string;
  complianceStatus: string;
  dataGaps: string[];
  ein: string;
  entityType: string;
  filingDate: string;
  filingFormType: string;
  filingParseStatus: string;
  filingTaxYear: string;
  filingsCount: number;
  highlights: string[];
  irsStatus: string;
  modelSource: string;
  modelVersion: string;
  name: string;
  nteeCategory: string;
  queryExecutionId: string;
  recent990OnFile: string;
  riskIndicators: string[];
  snapshotMaterializedAt: string;
  sourceSummaries: PortalNonprofitSourceSummary[];
  state: string;
  subsection: string;
  taxDeductible: string;
  taxPeriod: string;
}

export interface PortalNonprofitSearchPage {
  items: PortalNonprofitSearchSummary[];
  nextCursor: string | null;
}

export interface PortalNonprofitSearchService {
  lookupByEin(ein: string): Promise<PortalNonprofitDetail | null>;
  searchByName(
    query: string,
    options?: { cursor?: string | null; limit?: number },
  ): Promise<PortalNonprofitSearchPage>;
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
        const detail = await apiClient.get<BackendNonprofitDetailResponse>(
          apiEndpoints.nonprofits.detail,
          {
            pathParams: {
              ein: normalizedEin,
            },
          },
        );
        return mapDetail(detail);
      } catch (error) {
        if (error instanceof ApiRequestError && error.status === 404) {
          return null;
        }
        throw error;
      }
    },
    async searchByName(query, options) {
      const trimmedQuery = query.trim();
      if (!trimmedQuery) {
        return {
          items: [],
          nextCursor: null,
        };
      }

      const response = await apiClient.get<BackendNonprofitSearchResponse>(
        apiEndpoints.nonprofits.search,
        {
          query: {
            ...(options?.cursor ? { cursor: options.cursor } : {}),
            limit: options?.limit ?? 8,
            q: trimmedQuery,
          },
        },
      );

      return {
        items: (response.items ?? []).map(mapSearchSummary),
        nextCursor: normalizeOptionalText(response.pagination?.next_cursor),
      };
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

function mapDetail(detail: BackendNonprofitDetailResponse): PortalNonprofitDetail {
  const overview = detail.overview ?? {};
  const filings = detail.filings ?? {};
  const latestFiling = filings.latest ?? {};
  const signals = detail.signals ?? {};
  const snapshot = detail.snapshot ?? {};

  return {
    appearsBecause: normalizeStringList(signals.appears_because),
    complianceCheckType: normalizeText(
      detail.compliance?.check_type,
      "No compliance snapshot",
    ),
    complianceCheckedAt: normalizeText(
      detail.compliance?.evaluated_at,
      "No compliance timestamp",
    ),
    complianceStatus: normalizeText(
      detail.compliance?.status,
      "No compliance snapshot",
    ),
    dataGaps: normalizeStringList(signals.data_gaps),
    ein: normalizeText(detail.organization?.ein, "Unknown EIN"),
    entityType: normalizeText(overview.entity_type, "Unavailable"),
    filingDate: normalizeText(latestFiling.filing_date, "No filing date"),
    filingFormType: normalizeText(latestFiling.return_type, "No filing form"),
    filingParseStatus: normalizeText(
      latestFiling.parse_status,
      "No filing parse status",
    ),
    filingTaxYear: normalizeText(latestFiling.tax_year, "No filing year"),
    filingsCount:
      typeof filings.count === "number" && Number.isFinite(filings.count)
        ? filings.count
        : 0,
    highlights: normalizeStringList(signals.highlights),
    irsStatus: normalizeText(overview.irs_status, "Unavailable"),
    modelSource: "nonprofit_detail_snapshot",
    modelVersion: normalizeText(
      snapshot.renderer_version,
      normalizeText(snapshot.schema_version, "Unavailable"),
    ),
    name: normalizeText(detail.organization?.name, "Unknown organization"),
    nteeCategory: normalizeText(overview.ntee_category, "Unavailable"),
    queryExecutionId: normalizeText(snapshot.source_hash, "Not applicable"),
    recent990OnFile: formatOptionalBoolean(filings.recent_990_on_file, "Unknown"),
    riskIndicators: normalizeStringList(signals.risk_indicators),
    snapshotMaterializedAt: normalizeText(
      snapshot.materialized_at,
      "Unavailable",
    ),
    sourceSummaries: mapSourceSummaries(detail.sources ?? []),
    state: normalizeText(overview.state, "Unavailable"),
    subsection: normalizeText(overview.subsection, "Unavailable"),
    taxDeductible: normalizeText(overview.tax_deductible, "Unavailable"),
    taxPeriod: normalizeText(latestFiling.tax_period, "No tax period"),
  };
}

function mapSourceSummaries(
  sources: NonNullable<BackendNonprofitDetailResponse["sources"]>,
): PortalNonprofitSourceSummary[] {
  return sources
    .map((source) => {
      const sourceName = normalizeOptionalText(source.source_name);
      if (!sourceName) {
        return null;
      }

      return {
        category: normalizeText(source.category, "general"),
        explanation: normalizeText(source.explanation, "No explanation provided"),
        providerName: normalizeText(
          source.provider_name,
          humanizeIdentifier(sourceName),
        ),
        retrievedAt: normalizeText(source.retrieved_at, "Unknown"),
        sourceName,
        status: normalizeText(source.status, "unknown"),
        validAsOf: normalizeText(source.valid_as_of, "Unknown"),
      };
    })
    .filter((item): item is PortalNonprofitSourceSummary => item !== null);
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

function normalizeStringList(value: unknown): string[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => normalizeOptionalText(item))
    .filter((item): item is string => item !== null);
}

function normalizeText(value: unknown, fallback: string): string {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "boolean") {
    return String(value);
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }

  return fallback;
}

function normalizeOptionalText(value: unknown): string | null {
  if (typeof value === "string" && value.trim()) {
    return value.trim();
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    return String(value);
  }

  return null;
}

function formatOptionalBoolean(
  value: boolean | null | undefined,
  fallback: string,
): string {
  if (typeof value !== "boolean") {
    return fallback;
  }
  return value ? "true" : "false";
}

function humanizeIdentifier(value: string): string {
  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((segment) => segment[0]?.toUpperCase() + segment.slice(1))
    .join(" ");
}
