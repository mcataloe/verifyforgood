import { Stack, Text, Title } from "@mantine/core";
import { DetailFieldList } from "@charity-status/shared-ui";
import { getPortalAccessLabel } from "../app/portalNavigation";
import type { PortalAuthenticatedSession } from "../app/portalSession";
import type { PortalOrganizationContextValue } from "../organization/usePortalOrganization";

interface ProfileContextSectionProps {
  environment?: string;
  organization: PortalOrganizationContextValue["activeOrganization"];
  session: PortalAuthenticatedSession;
  showTitle?: boolean;
}

export function ProfileContextSection({
  environment: _environment,
  organization,
  session,
  showTitle = true,
}: ProfileContextSectionProps) {
  return (
    <Stack
      aria-labelledby={showTitle ? "profile-context-title" : undefined}
      gap="md"
    >
      {showTitle ? <Title id="profile-context-title" order={3}>Account Details</Title> : null}
      <Stack gap={2}>
        <Text fw={700} size="lg">
          {session.user.display_name}
        </Text>
        <Text c="dimmed">{session.user.email}</Text>
      </Stack>
      <DetailFieldList
        items={[
          {
            key: "organization",
            label: "Organization",
            value: organization.organization_name,
          },
          {
            key: "access",
            label: "Access",
            value: getPortalAccessLabel(session.roles),
          },
          {
            key: "plan",
            label: "Plan",
            value: session.plan,
          },
        ]}
      />
    </Stack>
  );
}
