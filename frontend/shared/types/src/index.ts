export {
  FRONTEND_ACCESS_ROLE,
  FRONTEND_ACCESS_ROLES,
  isFrontendAccessRole,
} from "./access";
export type { FrontendAccessRole } from "./access";

export type FrontendSurface = "docs" | "marketing" | "portal";

export interface FrontendAppInfo {
  surface: FrontendSurface;
  title: string;
  description: string;
  audience: string;
}

export type FrontendEnvironment =
  | "development"
  | "test"
  | "staging"
  | "production";

export interface FrontendRuntimeConfig {
  environment: FrontendEnvironment;
  apiBaseUrl: string;
  apiVersion: string;
  platformBaseUrl?: string;
}

export interface ApiDeprecationMetadata {
  status: string;
  sunset_date: string | null;
  recommended_version: string | null;
}

export interface ApiErrorDetail {
  code: string;
  message: string;
}

export interface ApiResponseEnvelope<
  TData = Record<string, unknown>,
  TMeta = Record<string, unknown>,
> {
  api_version: string;
  api_release: string;
  request_id: string;
  deprecation: ApiDeprecationMetadata;
  plan: string;
  data: TData;
  meta: TMeta;
  errors: ApiErrorDetail[];
}

export interface OrganizationContext {
  workspace_id?: string | null;
  account_id?: string | null;
}

export type PlanCode = "free" | "starter" | "growth" | "pro" | "enterprise";

export type PlanFeatureKey =
  | "verification"
  | "risk_flags"
  | "financial_trends"
  | "benchmarking"
  | "state_registry"
  | "monitoring"
  | "batch_verification"
  | "organization_settings";

export type PlanFeatureAvailability = Record<PlanFeatureKey, boolean>;

export interface PlanIncludedUsage {
  monthly_requests: number;
  batch_items: number;
  requests_per_minute: number;
}

export interface PlanPerRequestPricing {
  amount_usd_micros: number;
  currency_code: string;
  unit: string;
}

export interface PricingPlanMetadata {
  plan_code: PlanCode;
  display_name: string;
  included_usage: PlanIncludedUsage;
  per_request_pricing: PlanPerRequestPricing;
  feature_availability: PlanFeatureAvailability;
}

export interface PricingPlanCatalogResponse {
  plans: PricingPlanMetadata[];
}
