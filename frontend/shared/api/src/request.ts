import type {
  ApiResponseEnvelope,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type {
  ApiPathParams,
  ApiQueryParams,
  ApiRequestMethod,
  ApiRouteTarget,
} from "./routes";
import { buildApiUrl } from "./routes";

type ApiRuntimeConfig = Pick<
  FrontendRuntimeConfig,
  "apiBaseUrl" | "apiVersion"
>;

type FetchLike = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

export interface ApiHeadersProviderContext<TBody = unknown> {
  body?: TBody;
  headers: Headers;
  method: ApiRequestMethod;
  runtimeConfig: ApiRuntimeConfig;
  signal?: AbortSignal;
  target: ApiRouteTarget;
}

export type ApiHeadersProvider<TBody = unknown> = (
  context: ApiHeadersProviderContext<TBody>,
) => HeadersInit | Promise<HeadersInit | void> | void;

export interface ApiClientConfig {
  fetchImpl?: FetchLike;
  credentials?: RequestCredentials;
  headersProvider?: ApiHeadersProvider;
  runtimeConfig: ApiRuntimeConfig;
}

export interface ApiRequestOptions<TBody = undefined> {
  body?: TBody;
  credentials?: RequestCredentials;
  fetchImpl?: FetchLike;
  headers?: HeadersInit;
  headersProvider?: ApiHeadersProvider<TBody>;
  method?: ApiRequestMethod;
  pathParams?: ApiPathParams;
  query?: ApiQueryParams;
  runtimeConfig: ApiRuntimeConfig;
  signal?: AbortSignal;
}

export type ApiClientRequestOptions<TBody = undefined> = Omit<
  ApiRequestOptions<TBody>,
  "fetchImpl" | "headersProvider" | "runtimeConfig"
>;

export type ApiRequestErrorDetails = Record<string, unknown>;

export class ApiRequestError<TMeta = Record<string, unknown>> extends Error {
  readonly status: number;
  readonly code: string;
  readonly requestId: string | null;
  readonly envelope: ApiResponseEnvelope<unknown, TMeta> | null;
  readonly meta: TMeta | null;
  readonly details: ApiRequestErrorDetails | null;
  readonly payload: unknown;
  readonly rawBody: string | null;

  constructor(
    message: string,
    {
      code,
      details,
      envelope,
      meta,
      payload,
      rawBody,
      requestId,
      status,
    }: {
      code: string;
      details: ApiRequestErrorDetails | null;
      envelope: ApiResponseEnvelope<unknown, TMeta> | null;
      meta: TMeta | null;
      payload: unknown;
      rawBody: string | null;
      requestId: string | null;
      status: number;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.envelope = envelope;
    this.meta = meta;
    this.details = details;
    this.payload = payload;
    this.rawBody = rawBody;
  }
}

export interface ApiClient {
  delete<TData>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions,
  ): Promise<TData>;
  get<TData>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions,
  ): Promise<TData>;
  patch<TData, TBody = unknown>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions<TBody>,
  ): Promise<TData>;
  post<TData, TBody = unknown>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions<TBody>,
  ): Promise<TData>;
  put<TData, TBody = unknown>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions<TBody>,
  ): Promise<TData>;
  requestData<TData, TBody = undefined>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions<TBody>,
  ): Promise<TData>;
  requestEnvelope<TData, TBody = undefined, TMeta = Record<string, unknown>>(
    target: ApiRouteTarget,
    options?: ApiClientRequestOptions<TBody>,
  ): Promise<ApiResponseEnvelope<TData, TMeta>>;
}

export function createApiClient(config: ApiClientConfig): ApiClient {
  return {
    delete(target, options) {
      return del(target, withClientConfig(config, options));
    },
    get(target, options) {
      return get(target, withClientConfig(config, options));
    },
    patch(target, options) {
      return patch(target, withClientConfig(config, options));
    },
    post(target, options) {
      return post(target, withClientConfig(config, options));
    },
    put(target, options) {
      return put(target, withClientConfig(config, options));
    },
    requestData(target, options) {
      return requestData(target, withClientConfig(config, options));
    },
    requestEnvelope(target, options) {
      return requestEnvelope(target, withClientConfig(config, options));
    },
  };
}

export async function requestEnvelope<
  TData,
  TBody = undefined,
  TMeta = Record<string, unknown>,
>(
  target: ApiRouteTarget,
  options: ApiRequestOptions<TBody>,
): Promise<ApiResponseEnvelope<TData, TMeta>> {
  const method = resolveMethod(target, options.method);
  const fetchImpl = options.fetchImpl ?? fetch;
  const headers = await buildHeaders(target, method, options);
  const response = await fetchImpl(
    buildApiUrl(target, options.runtimeConfig, {
      pathParams: options.pathParams,
      preserveUnresolved: false,
      query: options.query,
    }),
    {
      body:
        options.body === undefined ? undefined : JSON.stringify(options.body),
      credentials: options.credentials,
      headers,
      method,
      signal: options.signal,
    },
  );

  const rawBody = await response.text();
  const payload = parsePayload(rawBody);
  const envelope = isApiResponseEnvelope<TData, TMeta>(payload)
    ? payload
    : null;

  if (response.ok && envelope && envelope.errors.length === 0) {
    return envelope;
  }

  throw createApiRequestError(response.status, envelope, payload, rawBody);
}

export async function requestData<TData, TBody = undefined>(
  target: ApiRouteTarget,
  options: ApiRequestOptions<TBody>,
): Promise<TData> {
  const envelope = await requestEnvelope<TData, TBody>(target, options);
  return envelope.data;
}

export function requestApi<
  TData,
  TBody = undefined,
  TMeta = Record<string, unknown>,
>(
  target: ApiRouteTarget,
  options: ApiRequestOptions<TBody>,
): Promise<ApiResponseEnvelope<TData, TMeta>> {
  return requestEnvelope<TData, TBody, TMeta>(target, options);
}

export function get<TData>(
  target: ApiRouteTarget,
  options: Omit<ApiRequestOptions, "body" | "method">,
): Promise<TData> {
  return requestData<TData>(target, {
    ...options,
    method: "GET",
  });
}

export function post<TData, TBody = unknown>(
  target: ApiRouteTarget,
  options: Omit<ApiRequestOptions<TBody>, "method">,
): Promise<TData> {
  return requestData<TData, TBody>(target, {
    ...options,
    method: "POST",
  });
}

export function put<TData, TBody = unknown>(
  target: ApiRouteTarget,
  options: Omit<ApiRequestOptions<TBody>, "method">,
): Promise<TData> {
  return requestData<TData, TBody>(target, {
    ...options,
    method: "PUT",
  });
}

export function patch<TData, TBody = unknown>(
  target: ApiRouteTarget,
  options: Omit<ApiRequestOptions<TBody>, "method">,
): Promise<TData> {
  return requestData<TData, TBody>(target, {
    ...options,
    method: "PATCH",
  });
}

export function del<TData>(
  target: ApiRouteTarget,
  options: Omit<ApiRequestOptions, "body" | "method">,
): Promise<TData> {
  return requestData<TData>(target, {
    ...options,
    method: "DELETE",
  });
}

function withClientConfig<TBody>(
  config: ApiClientConfig,
  options?: ApiClientRequestOptions<TBody>,
): ApiRequestOptions<TBody> {
  return {
    ...(options ?? {}),
    credentials: options?.credentials ?? config.credentials,
    fetchImpl: config.fetchImpl,
    headersProvider: config.headersProvider as
      | ApiHeadersProvider<TBody>
      | undefined,
    runtimeConfig: config.runtimeConfig,
  };
}

async function buildHeaders<TBody>(
  target: ApiRouteTarget,
  method: ApiRequestMethod,
  options: ApiRequestOptions<TBody>,
): Promise<Headers> {
  const headers = new Headers({
    Accept: "application/json",
    ...(options.headers ?? {}),
  });

  if (options.body !== undefined && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const headerContext: ApiHeadersProviderContext<TBody> = {
    body: options.body,
    headers,
    method,
    runtimeConfig: options.runtimeConfig,
    signal: options.signal,
    target,
  };

  await applyProvidedHeaders(headers, options.headersProvider, headerContext);

  return headers;
}

async function applyProvidedHeaders<TBody>(
  headers: Headers,
  provider: ApiHeadersProvider<TBody> | undefined,
  context: ApiHeadersProviderContext<TBody>,
): Promise<void> {
  const providedHeaders = await provider?.(context);
  if (!providedHeaders) {
    return;
  }

  const normalizedHeaders = new Headers(providedHeaders);
  normalizedHeaders.forEach((value, key) => {
    headers.set(key, value);
  });
}

function resolveMethod(
  target: ApiRouteTarget,
  method?: ApiRequestMethod,
): ApiRequestMethod {
  if (method) {
    return method;
  }

  if (typeof target === "string") {
    return "GET";
  }

  return target.method;
}

function parsePayload(rawBody: string): unknown {
  if (!rawBody) {
    return null;
  }

  try {
    return JSON.parse(rawBody) as unknown;
  } catch {
    return null;
  }
}

function isApiResponseEnvelope<TData, TMeta>(
  payload: unknown,
): payload is ApiResponseEnvelope<TData, TMeta> {
  if (!payload || typeof payload !== "object") {
    return false;
  }

  const candidate = payload as Partial<ApiResponseEnvelope<TData, TMeta>>;
  return (
    Array.isArray(candidate.errors) &&
    typeof candidate.api_version === "string" &&
    typeof candidate.api_release === "string" &&
    typeof candidate.request_id === "string"
  );
}

function createApiRequestError<TMeta>(
  status: number,
  envelope: ApiResponseEnvelope<unknown, TMeta> | null,
  payload: unknown,
  rawBody: string,
): ApiRequestError<TMeta> {
  if (envelope) {
    const firstError = envelope.errors[0];
    return new ApiRequestError<TMeta>(firstError?.message ?? "Request failed", {
      code: firstError?.code ?? statusToErrorCode(status),
      details: normalizeDetails(envelope.meta),
      envelope,
      meta: envelope.meta ?? null,
      payload,
      rawBody: rawBody || null,
      requestId: envelope.request_id ?? null,
      status,
    });
  }

  if (payload && typeof payload === "object") {
    const candidate = payload as Record<string, unknown>;
    return new ApiRequestError<TMeta>(
      normalizeMessage(candidate.message, status),
      {
        code:
          typeof candidate.code === "string"
            ? candidate.code
            : statusToErrorCode(status),
        details: normalizeObjectDetails(candidate.details),
        envelope: null,
        meta: null,
        payload,
        rawBody: rawBody || null,
        requestId:
          typeof candidate.request_id === "string"
            ? candidate.request_id
            : null,
        status,
      },
    );
  }

  return new ApiRequestError<TMeta>(normalizeMessage(rawBody, status), {
    code: statusToErrorCode(status),
    details: null,
    envelope: null,
    meta: null,
    payload: null,
    rawBody: rawBody || null,
    requestId: null,
    status,
  });
}

function normalizeDetails(meta: unknown): ApiRequestErrorDetails | null {
  if (!meta || typeof meta !== "object") {
    return null;
  }

  const candidate = meta as Record<string, unknown>;
  return normalizeObjectDetails(candidate.details);
}

function normalizeObjectDetails(
  details: unknown,
): ApiRequestErrorDetails | null {
  if (!details || typeof details !== "object" || Array.isArray(details)) {
    return null;
  }

  return details as ApiRequestErrorDetails;
}

function normalizeMessage(candidate: unknown, status: number): string {
  if (typeof candidate === "string" && candidate.trim()) {
    return candidate.trim();
  }

  return `API request failed with status ${status}`;
}

function statusToErrorCode(status: number): string {
  if (status === 400) {
    return "bad_request";
  }
  if (status === 401) {
    return "unauthorized";
  }
  if (status === 402) {
    return "billing_restricted";
  }
  if (status === 403) {
    return "forbidden";
  }
  if (status === 404) {
    return "not_found";
  }
  if (status === 429) {
    return "rate_limited";
  }
  if (status >= 500) {
    return "internal_error";
  }
  return "error";
}
