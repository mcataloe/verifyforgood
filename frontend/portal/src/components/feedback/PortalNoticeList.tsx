import { Alert, Stack } from "@mantine/core";
import type { ReactNode } from "react";

export interface PortalNoticeListItem {
  body: ReactNode;
  id: string;
  title?: string;
  tone: "empty" | "error" | "loading" | "warning";
}

interface PortalNoticeListProps {
  notices: PortalNoticeListItem[];
  onDismiss?: (id: string) => void;
}

export function PortalNoticeList({
  notices,
  onDismiss,
}: PortalNoticeListProps) {
  if (notices.length === 0) {
    return null;
  }

  return (
    <Stack gap="sm">
      {notices.map((notice) => (
        <Alert
          closeButtonLabel={`Dismiss ${notice.title ?? "notification"}`}
          color={resolveNoticeColor(notice.tone)}
          key={notice.id}
          onClose={onDismiss ? () => onDismiss(notice.id) : undefined}
          radius="md"
          title={notice.title}
          variant="light"
          withCloseButton={Boolean(onDismiss)}
        >
          {notice.body}
        </Alert>
      ))}
    </Stack>
  );
}

function resolveNoticeColor(tone: PortalNoticeListItem["tone"]) {
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
