import { Button, Group, Menu, Stack, Text } from "@mantine/core";
import type { PortalAvailableOrganizationRecord } from "../app/portalSession";

interface PortalOrganizationSwitcherProps {
  activeOrganizationId?: string | null;
  activeOrganizationName: string;
  availableOrganizations: readonly PortalAvailableOrganizationRecord[];
  onSelectOrganization: (
    organization: PortalAvailableOrganizationRecord,
  ) => void;
}

export function PortalOrganizationSwitcher({
  activeOrganizationId,
  activeOrganizationName,
  availableOrganizations,
  onSelectOrganization,
}: PortalOrganizationSwitcherProps) {
  if (availableOrganizations.length <= 1) {
    return (
      <Stack
        data-testid="portal-current-organization"
        gap={0}
        style={{ minWidth: 0 }}
      >
        <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
          Organization
        </Text>
        <Text fw={600} style={{ maxWidth: "18rem" }} truncate>
          {activeOrganizationName}
        </Text>
      </Stack>
    );
  }

  return (
    <Menu keepMounted position="bottom-end" shadow="md" width={320} withinPortal={false}>
      <Menu.Target>
        <Button
          data-testid="portal-organization-switcher"
          justify="space-between"
          variant="default"
        >
          <Group gap="xs" wrap="nowrap">
            <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
              Organization
            </Text>
            <Text fw={600} maw={180} truncate>
              {activeOrganizationName}
            </Text>
          </Group>
        </Button>
      </Menu.Target>

      <Menu.Dropdown data-testid="portal-organization-switcher-dropdown">
        <Menu.Label>Switch organization</Menu.Label>
        {availableOrganizations.map((organization) => {
          const isCurrent =
            organization.organization_id === activeOrganizationId;

          return (
            <Menu.Item
              data-testid={`portal-organization-option-${organization.slug}`}
              disabled={isCurrent}
              key={organization.organization_id}
              onClick={() => onSelectOrganization(organization)}
              rightSection={
                isCurrent ? (
                  <Text c="dimmed" fz="xs" fw={600}>
                    Current
                  </Text>
                ) : null
              }
            >
              <Stack gap={0}>
                <Text fw={600}>{organization.organization_name}</Text>
                <Text c="dimmed" fz="xs">
                  {organization.membership.role === "admin"
                    ? "Admin access"
                    : "Member access"}
                </Text>
              </Stack>
            </Menu.Item>
          );
        })}
      </Menu.Dropdown>
    </Menu>
  );
}
