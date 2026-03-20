import type { ApiResponseEnvelope, FrontendRuntimeConfig } from "@charity-status/shared-types";
import { buildApiUrl } from "./routes";

type ApiRuntimeConfig = Pick<FrontendRuntimeConfig, "apiBaseUrl" | "apiVersion">;

export type ApiRequestMethod = "DELETE" | "GET" | "PATCH" | "POST" | "PUT";

type FetchLike = (input: RequestInfo | URL, init?: RequestInit) => Promise<Response>;

export interface ApiRequestOptions<TBody> {
  runtimeConfig: ApiRuntimeConfig;
  method?: ApiRequestMethod;
  body?: TBody;
  headers?: HeadersInit;
  signal?: AbortSignal;
  fetchImpl?: FetchLike;
}

export class ApiRequestError<TMeta = Record<string, unknown>> extends Error {
  readonly status: number;
  readonly code: string | null;
  readonly envelope: ApiResponseEnvelope<unknown, TMeta> | null;

  constructor(
    message: string,
    {
      status,
      envelope,
    }: {
      status: number;
      envelope: ApiResponseEnvelope<unknown, TMeta> | null;
    },
  ) {
    super(message);
    this.name = "ApiRequestError";
    this.status = status;
    this.code = envelope?.errors[0]?.code ?? null;
    this.envelope = envelope;
  }
}

export async function requestApi<
  TData,
  TBody = undefined,
  TMeta = Record<string, unknown>,
>(
  path: string,
  options: ApiRequestOptions<TBody>,
): Promise<ApiResponseEnvelope<TData, TMeta>> {
  const fetchImpl = options.fetchImpl ?? fetch;
  const response = await fetchImpl(buildApiUrl(path, options.runtimeConfig), {
    method: options.method ?? "GET",
    headers: buildHeaders(options.body, options.headers),
    body: options.body === undefined ? undefined : JSON.stringify(options.body),
    signal: options.signal,
  });

  const envelope = (await response.json()) as ApiResponseEnvelope<TData, TMeta>;
  if (!response.ok || envelope.errors.length > 0) {
    const firstError = envelope.errors[0];
    throw new ApiRequestError(firstError?.message ?? "Request failed", {
      status: response.status,
      envelope,
    });
  }

  return envelope;
}

function buildHeaders(body: unknown, headers?: HeadersInit): HeadersInit {
  if (body === undefined) {
    return headers ?? {};
  }
  return {
    "Content-Type": "application/json",
    ...(headers ?? {}),
  };
}
