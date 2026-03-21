import { describe, expect, it } from "vitest";
import { ApiRequestError } from "@charity-status/shared-api";
import { normalizePortalError } from "./portalError";

describe("normalizePortalError", () => {
  it("keeps API client messages when present", () => {
    const error = new ApiRequestError("Quota reached.", {
      code: "quota_exceeded_hard_stop",
      details: null,
      envelope: null,
      meta: null,
      payload: null,
      rawBody: null,
      requestId: "req_123",
      status: 429,
    });

    expect(normalizePortalError(error, "Fallback")).toBe("Quota reached.");
  });

  it("falls back to portal-specific copy for API request codes", () => {
    const error = new ApiRequestError("", {
      code: "billing_restricted",
      details: null,
      envelope: null,
      meta: null,
      payload: null,
      rawBody: null,
      requestId: "req_456",
      status: 402,
    });

    expect(normalizePortalError(error, "Fallback")).toMatch(
      /Billing access is currently restricted/i,
    );
  });
});
