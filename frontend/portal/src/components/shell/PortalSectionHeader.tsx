import { PageHeader } from "@charity-status/shared-ui";
import type { ReactNode } from "react";

interface PortalSectionHeaderProps {
  action?: ReactNode;
  description?: string;
  eyebrow?: string;
  title: string;
}

export function PortalSectionHeader({
  action,
  description,
  title,
}: PortalSectionHeaderProps) {
  return (
    <PageHeader actions={action} description={description} title={title} />
  );
}
