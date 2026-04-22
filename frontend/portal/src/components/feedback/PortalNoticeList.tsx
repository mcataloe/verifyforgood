import { Stack } from "@mantine/core";
import type { ReactNode } from "react";
import { PortalNotice } from "./PortalNotice";

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
        <PortalNotice
          key={notice.id}
          onDismiss={onDismiss ? () => onDismiss(notice.id) : undefined}
          title={notice.title}
          tone={notice.tone}
        >
          {notice.body}
        </PortalNotice>
      ))}
    </Stack>
  );
}
