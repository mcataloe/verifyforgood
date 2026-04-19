import { Alert, Stack } from "@mantine/core";
import type { PropsWithChildren, ReactNode } from "react";

interface PortalNoticeProps extends PropsWithChildren {
  action?: ReactNode;
  title?: string;
  tone: "empty" | "error" | "loading" | "warning";
}

export function PortalNotice({
  action,
  children,
  title,
  tone,
}: PortalNoticeProps) {
  return (
    <Alert color={resolveNoticeColor(tone)} radius="md" title={title} variant="light">
      <Stack gap="sm">
        <div>{children}</div>
        {action}
      </Stack>
    </Alert>
  );
}

function resolveNoticeColor(tone: PortalNoticeProps["tone"]) {
  switch (tone) {
    case "error":
      return "red";
    case "loading":
      return "blue";
    case "empty":
    case "warning":
    default:
      return "teal";
  }
}
