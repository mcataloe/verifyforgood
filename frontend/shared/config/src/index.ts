import type {
  FrontendEnvironment,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";

export interface SharedEnvSource {
  MODE?: string;
  VITE_API_BASE_URL?: string;
  VITE_API_VERSION?: string;
  VITE_APP_ENVIRONMENT?: string;
  VITE_PLATFORM_BASE_URL?: string;
}

const DEFAULT_API_VERSION = "v1";

export function normalizeApiVersion(value?: string): string {
  const normalized = String(value || DEFAULT_API_VERSION)
    .trim()
    .replace(/^\/+/, "")
    .replace(/\/+$/, "");
  return normalized || DEFAULT_API_VERSION;
}

export function normalizeBaseUrl(value?: string): string {
  const candidate = String(value || "").trim();
  return candidate.replace(/\/+$/, "");
}

export function resolveFrontendEnvironment(
  explicitEnvironment?: string,
  mode?: string,
): FrontendEnvironment {
  const candidate = String(explicitEnvironment || mode || "")
    .trim()
    .toLowerCase();

  if (candidate === "production" || candidate === "prod") {
    return "production";
  }
  if (candidate === "test") {
    return "test";
  }
  if (candidate === "staging" || candidate === "stage") {
    return "staging";
  }
  return "development";
}

export function readRuntimeConfig(
  source: SharedEnvSource,
): FrontendRuntimeConfig {
  return {
    environment: resolveFrontendEnvironment(
      source.VITE_APP_ENVIRONMENT,
      source.MODE,
    ),
    apiBaseUrl: normalizeBaseUrl(source.VITE_API_BASE_URL),
    apiVersion: normalizeApiVersion(source.VITE_API_VERSION),
    platformBaseUrl: normalizeBaseUrl(source.VITE_PLATFORM_BASE_URL),
  };
}
