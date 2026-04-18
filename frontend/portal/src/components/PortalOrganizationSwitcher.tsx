import { Button, Group, Menu, Stack, Text } from "@mantine/core";
import { IconChevronDown, IconPlus } from "@tabler/icons-react";
import type { PortalAvailableOrganizationRecord } from "../app/portalSession";

interface PortalOrganizationSwitcherProps {
  activeOrganizationId?: string | null;
  activeOrganizationName: string;
  availableOrganizations: readonly PortalAvailableOrganizationRecord[];
  onCreateOrganization?: () => void;
  onSelectOrganization: (
    organization: PortalAvailableOrganizationRecord,
  ) => void;
}

export function PortalOrganizationSwitcher({
  activeOrganizationId,
  activeOrganizationName,
  availableOrganizations,
  onCreateOrganization,
  onSelectOrganization,
}: PortalOrganizationSwitcherProps) {
  const hasDropdownActions =
    availableOrganizations.length > 0 || onCreateOrganization !== undefined;

  if (!hasDropdownActions) {
    return (
      <Stack
        data-testid="portal-current-organization"
        gap={0}
        style={{ minWidth: 0 }}
      >
        <Text fw={600} style={{ maxWidth: "18rem" }} truncate>
          {activeOrganizationName}
        </Text>
      </Stack>
    );
  }

  return (
    <Menu keepMounted position="bottom-end" shadow="md" width={320}>
      <Menu.Target>
        <Button
          data-testid="portal-organization-switcher"
          justify="space-between"
          rightSection={<IconChevronDown size={16} stroke={1.8} />}
          variant="default"
        >
          <Text fw={600} maw={220} truncate>
            {activeOrganizationName}
          </Text>
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
                    : "User access"}
                </Text>
              </Stack>
            </Menu.Item>
          );
        })}
        {availableOrganizations.length === 0 ? (
          <Menu.Item disabled>No organizations available yet</Menu.Item>
        ) : null}
        {onCreateOrganization ? (
          <>
            <Menu.Divider />
            <Menu.Item
              leftSection={<IconPlus size={16} stroke={1.8} />}
              onClick={onCreateOrganization}
            >
              Create organization
            </Menu.Item>
          </>
        ) : null}
      </Menu.Dropdown>
    </Menu>
  );
}
