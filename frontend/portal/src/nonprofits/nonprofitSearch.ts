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
  review?: BackendReviewEnvelope | null;
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
  source_availability?: Array<{
    attempted?: boolean | null;
    integration_id?: string | null;
    label?: string | null;
    status?: string | null;
  }> | null;
}

interface BackendReviewEnvelope {
  contract_version?: string | null;
  customer_decision?: unknown;
  evidence_review?: {
    checks?: BackendReviewCheck[];
    issues?: BackendReviewIssue[];
    source_coverage?: {
      completed?: string[] | null;
      not_checked?: string[] | null;
      required?: string[] | null;
      unavailable?: string[] | null;
    } | null;
    status?: string | null;
  } | null;
  requirements_evaluation?: BackendRequirementsEvaluation | null;
}

interface BackendReviewCheck {
  authoritative_for_policy?: boolean | null;
  category?: string | null;
  check_id?: string | null;
  freshness_status?: string | null;
  label?: string | null;
  limitations?: unknown;
  match_confidence?: string | number | null;
  observed_value?: unknown;
  retrieved_at?: string | null;
  source_references?: Array<{
    provider_name?: string | null;
    retrieved_at?: string | null;
    source_name?: string | null;
    valid_as_of?: string | null;
  }> | null;
  status?: string | null;
  valid_as_of?: string | null;
}

interface BackendReviewIssue {
  code?: string | null;
  message?: string | null;
  related_check_ids?: string[] | null;
  severity?: string | null;
}

interface BackendRequirementsEvaluation {
  adoption_status?: string | null;
  policy_effective_at?: string | null;
  policy_id?: string | null;
  policy_owner?: string | null;
  policy_version?: string | null;
  requirements?: Array<{
    description?: string | null;
    evidence_check_ids?: string[] | null;
    explanation?: string | null;
    requirement_id?: string | null;
    result?: string | null;
  }> | null;
  result?: string | null;
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

export interface PortalNonprofitSourceAvailability {
  attempted: boolean;
  integrationId: string;
  label: string;
  status: string;
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
  review: PortalReviewEnvelope | null;
  riskIndicators: string[];
  snapshotMaterializedAt: string;
  sourceAvailability: PortalNonprofitSourceAvailability[];
  sourceSummaries: PortalNonprofitSourceSummary[];
  state: string;
  subsection: string;
  taxDeductible: string;
  taxPeriod: string;
}

export interface PortalReviewEnvelope {
  contractVersion: string;
  customerDecision: string | null;
  evidenceReview: {
    checks: PortalReviewCheck[];
    issues: PortalReviewIssue[];
    sourceCoverage: {
      completed: string[];
      notChecked: string[];
      required: string[];
      unavailable: string[];
    };
    status: string;
  };
  requirementsEvaluation: PortalRequirementsEvaluation | null;
}

export interface PortalReviewCheck {
  authoritativeForPolicy: boolean;
  category: string;
  checkId: string;
  freshnessStatus: string;
  label: string;
  limitations: string[];
  matchConfidence: string;
  observedValue: string;
  retrievedAt: string;
  sourceReferences: PortalReviewSourceReference[];
  status: string;
  validAsOf: string;
}

export interface PortalReviewSourceReference {
  providerName: string;
  retrievedAt: string;
  sourceName: string;
  validAsOf: string;
}

export interface PortalReviewIssue {
  code: string;
  message: string;
  relatedCheckIds: string[];
  severity: string;
}

export interface PortalRequirementsEvaluation {
  adoptionStatus: string;
  policyEffectiveAt: string;
  policyId: string;
  policyOwner: string;
  policyVersion: string;
  requirements: PortalRequirementResult[];
  result: string;
}

export interface PortalRequirementResult {
  description: string;
  evidenceCheckIds: string[];
  explanation: string;
  requirementId: string;
  result: string;
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

function mapDetail(
  detail: BackendNonprofitDetailResponse,
): PortalNonprofitDetail {
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
    recent990OnFile: formatOptionalBoolean(
      filings.recent_990_on_file,
      "Unknown",
    ),
    review: mapReview(detail.review),
    riskIndicators: normalizeStringList(signals.risk_indicators),
    snapshotMaterializedAt: normalizeText(
      snapshot.materialized_at,
      "Unavailable",
    ),
    sourceAvailability: mapSourceAvailability(
      detail.source_availability ?? [],
      detail.sources ?? [],
    ),
    sourceSummaries: mapSourceSummaries(detail.sources ?? []),
    state: normalizeText(overview.state, "Unavailable"),
    subsection: normalizeText(overview.subsection, "Unavailable"),
    taxDeductible: normalizeText(overview.tax_deductible, "Unavailable"),
    taxPeriod: normalizeText(latestFiling.tax_period, "No tax period"),
  };
}

function mapSourceAvailability(
  availability: NonNullable<BackendNonprofitDetailResponse["source_availability"]>,
  sources: NonNullable<BackendNonprofitDetailResponse["sources"]>,
): PortalNonprofitSourceAvailability[] {
  if (availability.length > 0) {
    return availability.map((source, index) => ({
      attempted: Boolean(source.attempted),
      integrationId: normalizeText(source.integration_id, `source_${index}`),
      label: normalizeText(source.label, `Source ${index + 1}`),
      status: normalizeText(source.status, "unknown"),
    }));
  }

  return sources.map((source, index) => {
    const sourceName = normalizeText(source.source_name, `source_${index}`);
    return {
      attempted: true,
      integrationId: sourceName,
      label: normalizeText(source.provider_name, humanizeIdentifier(sourceName)),
      status: normalizeText(source.status, "unknown"),
    };
  });
}

function mapReview(
  review: BackendReviewEnvelope | null | undefined,
): PortalReviewEnvelope | null {
  if (!review?.evidence_review) {
    return null;
  }
  const coverage = review.evidence_review.source_coverage ?? {};
  return {
    contractVersion: normalizeText(review.contract_version, "1.0"),
    customerDecision: normalizeOptionalText(review.customer_decision),
    evidenceReview: {
      checks: (review.evidence_review.checks ?? []).map(mapReviewCheck),
      issues: (review.evidence_review.issues ?? []).map(mapReviewIssue),
      sourceCoverage: {
        completed: normalizeStringList(coverage.completed),
        notChecked: normalizeStringList(coverage.not_checked),
        required: normalizeStringList(coverage.required),
        unavailable: normalizeStringList(coverage.unavailable),
      },
      status: normalizeText(review.evidence_review.status, "not_recorded"),
    },
    requirementsEvaluation: mapRequirementsEvaluation(
      review.requirements_evaluation,
    ),
  };
}

function mapReviewCheck(check: BackendReviewCheck): PortalReviewCheck {
  return {
    authoritativeForPolicy: check.authoritative_for_policy === true,
    category: normalizeText(check.category, "general"),
    checkId: normalizeText(check.check_id, "unknown_check"),
    freshnessStatus: normalizeText(check.freshness_status, "unknown"),
    label: normalizeText(check.label, "Evidence check"),
    limitations: normalizeStringList(check.limitations),
    matchConfidence: normalizeText(check.match_confidence, "Not applicable"),
    observedValue: formatObservedValue(check.observed_value),
    retrievedAt: normalizeText(check.retrieved_at, "Unknown"),
    sourceReferences: (check.source_references ?? []).map((source) => ({
      providerName: normalizeText(source.provider_name, "Unknown provider"),
      retrievedAt: normalizeText(source.retrieved_at, "Unknown"),
      sourceName: normalizeText(source.source_name, "unknown_source"),
      validAsOf: normalizeText(source.valid_as_of, "Unknown"),
    })),
    status: normalizeText(check.status, "unknown"),
    validAsOf: normalizeText(check.valid_as_of, "Unknown"),
  };
}

function mapReviewIssue(issue: BackendReviewIssue): PortalReviewIssue {
  return {
    code: normalizeText(issue.code, "unknown_issue"),
    message: normalizeText(issue.message, "Review issue recorded."),
    relatedCheckIds: normalizeStringList(issue.related_check_ids),
    severity: normalizeText(issue.severity, "medium"),
  };
}

function mapRequirementsEvaluation(
  evaluation: BackendRequirementsEvaluation | null | undefined,
): PortalRequirementsEvaluation | null {
  if (!evaluation) {
    return null;
  }
  return {
    adoptionStatus: normalizeText(evaluation.adoption_status, "not_recorded"),
    policyEffectiveAt: normalizeText(
      evaluation.policy_effective_at,
      "Not recorded",
    ),
    policyId: normalizeText(evaluation.policy_id, "Unknown policy"),
    policyOwner: normalizeText(evaluation.policy_owner, "customer"),
    policyVersion: normalizeText(evaluation.policy_version, "Unknown version"),
    requirements: (evaluation.requirements ?? []).map((requirement) => ({
      description: normalizeText(
        requirement.description,
        "Customer requirement",
      ),
      evidenceCheckIds: normalizeStringList(requirement.evidence_check_ids),
      explanation: normalizeText(
        requirement.explanation,
        "No explanation recorded.",
      ),
      requirementId: normalizeText(
        requirement.requirement_id,
        "unknown_requirement",
      ),
      result: normalizeText(requirement.result, "unresolved"),
    })),
    result: normalizeText(evaluation.result, "unresolved"),
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
        explanation: normalizeText(
          source.explanation,
          "No explanation provided",
        ),
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

function formatObservedValue(value: unknown): string {
  if (value === null || value === undefined || value === "") {
    return "Not recorded";
  }
  if (Array.isArray(value)) {
    return value.length
      ? value.map(formatObservedValue).join(", ")
      : "None returned";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  return String(value);
}

function humanizeIdentifier(value: string): string {
  return value
    .split(/[_-]+/)
    .filter(Boolean)
    .map((segment) => segment[0]?.toUpperCase() + segment.slice(1))
    .join(" ");
}
