import type { FrontendRuntimeConfig } from "@charity-status/shared-types";
import {
  normalizeApiVersion,
  normalizeBaseUrl,
} from "@charity-status/shared-config";

type ApiRoutingConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

export type ApiRequestMethod = "DELETE" | "GET" | "PATCH" | "POST" | "PUT";

export interface ApiEndpointDescriptor {
  method: ApiRequestMethod;
  path: string;
  name?: string;
}

export type ApiRouteTarget = string | ApiEndpointDescriptor;

export type ApiPathParamValue = boolean | number | string;

export type ApiPathParams = Record<
  string,
  ApiPathParamValue | null | undefined
>;

export type ApiQueryParamValue =
  | ApiPathParamValue
  | ApiPathParamValue[]
  | null
  | undefined;

export type ApiQueryParams = Record<string, ApiQueryParamValue>;

export interface BuildApiPathOptions {
  pathParams?: ApiPathParams;
  preserveUnresolved?: boolean;
  query?: ApiQueryParams;
}

export function defineEndpoint(
  method: ApiRequestMethod,
  path: string,
  options?: Pick<ApiEndpointDescriptor, "name">,
): ApiEndpointDescriptor {
  return {
    method,
    path: normalizePath(path),
    ...(options ?? {}),
  };
}

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

export function resolvePathTemplate(
  path: string,
  pathParams?: ApiPathParams,
  options?: Pick<BuildApiPathOptions, "preserveUnresolved">,
): string {
  const normalizedPath = normalizePath(path);
  const preserveUnresolved = options?.preserveUnresolved ?? false;
  const replacedPath = normalizedPath.replace(
    /\{([^}]+)\}/g,
    (placeholder, key: string) => {
      const value = pathParams?.[key];
      if (value === null || value === undefined || value === "") {
        return preserveUnresolved ? placeholder : `__missing__:${key}`;
      }
      return encodeURIComponent(String(value));
    },
  );

  const unresolvedMatch = replacedPath.match(/__missing__:(\w+)/);
  if (unresolvedMatch) {
    throw new Error(`Missing API path parameter: ${unresolvedMatch[1]}`);
  }

  if (!preserveUnresolved && /\{[^}]+\}/.test(replacedPath)) {
    throw new Error(`Unresolved API path template: ${normalizedPath}`);
  }

  return replacedPath;
}

export function buildApiPath(
  target: ApiRouteTarget,
  apiVersion = "v1",
  options?: BuildApiPathOptions,
): string {
  const resolvedPath = resolvePathTemplate(
    typeof target === "string" ? target : target.path,
    options?.pathParams,
    {
      preserveUnresolved: options?.preserveUnresolved ?? true,
    },
  );
  const versionedPath = versionPath(resolvedPath, apiVersion);
  const queryString = buildQueryString(options?.query);

  return queryString ? `${versionedPath}?${queryString}` : versionedPath;
}

export function buildApiUrl(
  target: ApiRouteTarget,
  config: ApiRoutingConfig,
  options?: BuildApiPathOptions,
): string {
  const versionedPath = buildApiPath(target, config.apiVersion, options);
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

function buildQueryString(query?: ApiQueryParams): string {
  if (!query) {
    return "";
  }

  const searchParams = new URLSearchParams();

  for (const [key, value] of Object.entries(query)) {
    if (value === null || value === undefined) {
      continue;
    }

    if (Array.isArray(value)) {
      for (const item of value) {
        searchParams.append(key, String(item));
      }
      continue;
    }

    searchParams.append(key, String(value));
  }

  return searchParams.toString();
}
