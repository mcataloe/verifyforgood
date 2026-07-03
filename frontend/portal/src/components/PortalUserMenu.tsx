import { Avatar, Menu, Stack, Text, UnstyledButton } from "@mantine/core";
import { IconLogout, IconUserEdit } from "@tabler/icons-react";
import { useState } from "react";

interface PortalUserMenuProps {
  editProfileHref?: string;
  email?: string | null;
  onSignOut: () => void;
  primaryLabel: string;
}

export function PortalUserMenu({
  editProfileHref,
  email,
  onSignOut,
  primaryLabel,
}: PortalUserMenuProps) {
  const [menuOpened, setMenuOpened] = useState(false);

  return (
    <Menu
      keepMounted
      onChange={setMenuOpened}
      opened={menuOpened}
      position="bottom-end"
      shadow="md"
      width={260}
    >
      <Menu.Target>
        <UnstyledButton
          aria-expanded={menuOpened}
          aria-label={`${primaryLabel} account menu`}
          data-testid="portal-user-menu"
        >
          <Avatar color="dark" radius="xl" size={36}>
            {getInitials(primaryLabel)}
          </Avatar>
        </UnstyledButton>
      </Menu.Target>

      <Menu.Dropdown data-testid="portal-user-menu-dropdown">
        <Menu.Label>
          <Stack gap={0}>
            <Text fw={700} fz="sm">
              {primaryLabel}
            </Text>
            {email ? (
              <Text c="dimmed" fz="xs">
                {email}
              </Text>
            ) : null}
          </Stack>
        </Menu.Label>
        <Menu.Divider />
        {editProfileHref ? (
          <Menu.Item
            component="a"
            data-testid="portal-user-menu-edit-profile"
            href={editProfileHref}
            leftSection={<IconUserEdit size={16} stroke={1.8} />}
          >
            Edit profile
          </Menu.Item>
        ) : null}
        <Menu.Item
          color="red"
          data-testid="portal-user-menu-sign-out"
          leftSection={<IconLogout size={16} stroke={1.8} />}
          onClick={onSignOut}
        >
          Sign out
        </Menu.Item>
      </Menu.Dropdown>
    </Menu>
  );
}

function getInitials(value: string) {
  const initials = value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return initials || "VF";
}
