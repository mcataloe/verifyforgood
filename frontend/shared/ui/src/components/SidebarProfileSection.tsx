import { Box, Group, Stack, Text } from "@mantine/core";

export type SidebarProfileSectionProps = {
  accessLabel?: string;
  eyebrow?: string;
  primaryLabel: string;
  secondaryLabel?: string;
  tertiaryLabel?: string;
};

/**
 * Compact sidebar footer/profile block for user, organization, or account
 * context.
 */
export function SidebarProfileSection({
  accessLabel,
  eyebrow = "Profile",
  primaryLabel,
  secondaryLabel,
  tertiaryLabel,
}: SidebarProfileSectionProps) {
  return (
    <Stack className="vf-sidebar-profile" gap="sm">
      <Group align="flex-start" justify="space-between" wrap="nowrap">
        <Group className="vf-sidebar-profile__identity" gap="sm" wrap="nowrap">
          <Box aria-hidden="true" className="vf-sidebar-profile__avatar">
            {getProfileInitials(primaryLabel)}
          </Box>

          <Stack gap={2}>
            <Text className="vf-sidebar-profile__eyebrow" fz="xs" fw={600}>
              {eyebrow}
            </Text>
            <Text className="vf-sidebar-profile__primary" fw={700}>
              {primaryLabel}
            </Text>
            {secondaryLabel ? (
              <Text className="vf-sidebar-profile__secondary" fz="sm">
                {secondaryLabel}
              </Text>
            ) : null}
            {tertiaryLabel ? (
              <Text className="vf-sidebar-profile__tertiary" fz="sm">
                {tertiaryLabel}
              </Text>
            ) : null}
          </Stack>
        </Group>

        {accessLabel ? (
          <Text className="vf-sidebar-profile__access" fz="xs" fw={700}>
            {accessLabel}
          </Text>
        ) : null}
      </Group>
    </Stack>
  );
}

function getProfileInitials(value: string) {
  const initials = value
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return initials || "VF";
}
