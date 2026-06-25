import { describe, expect, it, vi } from "vitest";
import { authEndpoints, nonprofitEndpoints } from "./endpoints";
import {
  createApiClient,
  del,
  get,
  patch,
  post,
  put,
  requestData,
  requestEnvelope,
} from "./request";

const runtimeConfig = {
  apiBaseUrl: "https://api.verifyforgood.test",
  apiVersion: "v1",
} as const;

function buildEnvelope<TData, TMeta = Record<string, unknown>>(
  data: TData,
  overrides?: Partial<{
    api_release: string;
    api_version: string;
    deprecation: {
      recommended_version: string | null;
      status: string;
      sunset_date: string | null;
    };
    errors: Array<{ code: string; message: string }>;
    meta: TMeta;
    plan: string;
    request_id: string;
  }>,
) {
  return {
    api_release: "2026-03-20",
    api_version: "v1",
    data,
    deprecation: {
      recommended_version: null,
      status: "active",
      sunset_date: null,
    },
    errors: [],
    meta: {} as TMeta,
    plan: "basic",
    request_id: "req_test_123",
    ...overrides,
  };
}

function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    headers: {
      "Content-Type": "application/json",
    },
    status,
  });
}

function createFetchMock(
  responder: () => Response | Promise<Response>,
): typeof fetch {
  return vi.fn(async () => responder()) as unknown as typeof fetch;
}

describe("shared api request helpers", () => {
  it("returns envelopes and unwrapped data for successful requests", async () => {
    const fetchImpl = createFetchMock(() =>
      jsonResponse(
        buildEnvelope({
          ok: true,
        }),
      ),
    );

    const envelope = await requestEnvelope<{ ok: boolean }>(
      authEndpoints.oauthToken,
      {
        fetchImpl,
        runtimeConfig,
      },
    );
    const data = await requestData<{ ok: boolean }>(authEndpoints.oauthToken, {
      fetchImpl,
      runtimeConfig,
    });

    expect(envelope.data.ok).toBe(true);
    expect(data).toEqual({
      ok: true,
    });
    expect(fetchImpl).toHaveBeenNthCalledWith(
      1,
      "https://api.verifyforgood.test/v1/oauth/token",
      expect.objectContaining({
        body: undefined,
        method: "POST",
      }),
    );
  });

  it("merges default headers, request headers, and provider headers", async () => {
    const fetchImpl = createFetchMock(() =>
      jsonResponse(buildEnvelope({ ok: true })),
    );
    const client = createApiClient({
      credentials: "include",
      fetchImpl,
      headersProvider: async () => ({
        Authorization: "Bearer test-token",
      }),
      runtimeConfig,
    });

    await client.post(authEndpoints.oauthToken, {
      body: {
        client_id: "local",
      },
      headers: {
        "X-Request-Origin": "portal-local",
      },
    });

    expect(fetchImpl).toHaveBeenCalledWith(
      "https://api.verifyforgood.test/v1/oauth/token",
      expect.objectContaining({
        body: JSON.stringify({
          client_id: "local",
        }),
        headers: expect.any(Headers),
        method: "POST",
      }),
    );

    const fetchMock = vi.mocked(fetchImpl);
    const [, requestInit] = fetchMock.mock.calls[0] ?? [];
    const headers = requestInit?.headers as Headers;
    expect(headers.get("Accept")).toBe("application/json");
    expect(headers.get("Authorization")).toBe("Bearer test-token");
    expect(headers.get("Content-Type")).toBe("application/json");
    expect(headers.get("X-Request-Origin")).toBe("portal-local");
    expect(requestInit?.credentials).toBe("include");
  });

  it("normalizes envelope errors with backend metadata", async () => {
    const fetchImpl = createFetchMock(() =>
      jsonResponse(
        buildEnvelope(
          {},
          {
            errors: [
              {
                code: "forbidden",
                message: "Workspace access is required.",
              },
            ],
            meta: {
              details: {
                workspace_id: "ws_123",
              },
            },
          },
        ),
        403,
      ),
    );

    await expect(
      requestData(authEndpoints.oauthToken, {
        fetchImpl,
        runtimeConfig,
      }),
    ).rejects.toMatchObject({
      code: "forbidden",
      details: {
        workspace_id: "ws_123",
      },
      requestId: "req_test_123",
      status: 403,
    });
  });

  it("normalizes non-envelope json failures", async () => {
    const fetchImpl = createFetchMock(() =>
      jsonResponse(
        {
          code: "bad_request",
          details: {
            field: "ein",
          },
          message: "EIN is required.",
          request_id: "req_json_123",
        },
        400,
      ),
    );

    await expect(
      get(nonprofitEndpoints.search, {
        fetchImpl,
        runtimeConfig,
      }),
    ).rejects.toMatchObject({
      code: "bad_request",
      details: {
        field: "ein",
      },
      requestId: "req_json_123",
      status: 400,
    });
  });

  it("normalizes non-json failures with fallback error codes", async () => {
    const fetchImpl = createFetchMock(
      () =>
        new Response("Server unavailable", {
          status: 503,
        }),
    );

    await expect(
      get(nonprofitEndpoints.search, {
        fetchImpl,
        runtimeConfig,
      }),
    ).rejects.toMatchObject({
      code: "internal_error",
      rawBody: "Server unavailable",
      status: 503,
    });
  });

  it("uses the standard verb pipeline for GET, POST, PUT, PATCH, and DELETE", async () => {
    const fetchImpl = createFetchMock(() =>
      jsonResponse(buildEnvelope({ ok: true })),
    );

    await get(nonprofitEndpoints.search, {
      fetchImpl,
      query: {
        q: "education",
      },
      runtimeConfig,
    });
    await post(authEndpoints.oauthToken, {
      body: {
        grant_type: "client_credentials",
      },
      fetchImpl,
      runtimeConfig,
    });
    await put(authEndpoints.oauthToken, {
      body: {
        grant_type: "refresh_token",
      },
      fetchImpl,
      runtimeConfig,
    });
    await patch(authEndpoints.oauthToken, {
      body: {
        rotate: true,
      },
      fetchImpl,
      runtimeConfig,
    });
    await del(authEndpoints.oauthToken, {
      fetchImpl,
      runtimeConfig,
    });

    expect(
      vi
        .mocked(fetchImpl)
        .mock.calls.map(([, requestInit]) => requestInit?.method),
    ).toEqual(["GET", "POST", "PUT", "PATCH", "DELETE"]);
  });
});
