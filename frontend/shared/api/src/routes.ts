import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  normalizeApiVersion,
  normalizeBaseUrl,
} from "@charity-status/shared-config";

type ApiRoutingConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

export function versionPath(path: string, apiVersion = "v1"): string {
  const normalized = normalizePath(path);
  const versionPrefix = `/${normalizeApiVersion(apiVersion)}`;

  if (normalized === "/") {
    return versionPrefix;
  }
  if (
    normalized === versionPrefix ||
    normalized.startsWith(`${versionPrefix}/`)
  ) {
    return normalized;
  }
  return `${versionPrefix}${normalized}`;
}

export function stripVersionPrefix(path: string, apiVersion = "v1"): string {
  const normalized = normalizePath(path);
  const versionPrefix = `/${normalizeApiVersion(apiVersion)}`;

  if (normalized === versionPrefix) {
    return "/";
  }
  if (normalized.startsWith(`${versionPrefix}/`)) {
    return normalized.slice(versionPrefix.length) || "/";
  }
  return normalized;
}

export function normalizeRouteKey(routeKey: string, apiVersion = "v1"): string {
  const candidate = String(routeKey || "").trim();
  if (!candidate || !candidate.includes(" ")) {
    return candidate;
  }

  const [method, ...pathParts] = candidate.split(" ");
  const path = pathParts.join(" ").trim();
  return `${method.trim().toUpperCase()} ${versionPath(path, apiVersion)}`;
}

export function buildApiUrl(path: string, config: ApiRoutingConfig): string {
  const versionedPath = versionPath(path, config.apiVersion);
  const baseUrl = normalizeBaseUrl(config.apiBaseUrl);
  return baseUrl ? `${baseUrl}${versionedPath}` : versionedPath;
}

function normalizePath(path: string): string {
  const candidate = `/${String(path || "")
    .trim()
    .replace(/^\/+/, "")
    .replace(/\/+$/, "")}`;
  return candidate === "/" ? "/" : candidate;
}
