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
