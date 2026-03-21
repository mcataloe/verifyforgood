import { ApiRequestError } from "@charity-status/shared-api";

const PORTAL_ERROR_MESSAGES: Record<string, string> = {
  billing_restricted:
    "Billing access is currently restricted. Resolve billing status or update the current plan to continue.",
  forbidden:
    "You do not have permission to complete that action in this workspace.",
  internal_error:
    "The server could not complete that request. Try again in a moment.",
  not_found: "No matching record was found for that request.",
  quota_exceeded_hard_stop:
    "Monthly request limit reached. Upgrade the plan or enable overage to continue.",
  rate_limited:
    "Too many requests were sent at once. Wait a moment and try again.",
  unauthorized:
    "Your session is no longer authorized for that request. Sign in again and retry.",
};

export function normalizePortalError(
  error: unknown,
  fallbackMessage: string,
): string {
  if (error instanceof ApiRequestError) {
    if (error.message && error.message.trim()) {
      return error.message.trim();
    }

    return PORTAL_ERROR_MESSAGES[error.code] ?? fallbackMessage;
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }

  return fallbackMessage;
}
