import { Box, Group, Stack, Text, UnstyledButton } from "@mantine/core";
import type { MouseEvent } from "react";

export type SidebarProfileSectionProps = {
  active?: boolean;
  actionAriaLabel?: string;
  actionHref?: string;
  actionLabel?: string;
  actionOnClick?: () => void;
  ariaLabel?: string;
  eyebrow?: string;
  href?: string;
  onClick?: () => void;
  primaryLabel: string;
  secondaryLabel?: string;
  tertiaryLabel?: string;
};

/**
 * Compact sidebar footer/profile block for user, organization, or account
 * context.
 */
export function SidebarProfileSection({
  active = false,
  actionAriaLabel,
  actionHref,
  actionLabel,
  actionOnClick,
  ariaLabel,
  eyebrow = "Profile",
  href,
  onClick,
  primaryLabel,
  secondaryLabel,
  tertiaryLabel,
}: SidebarProfileSectionProps) {
  const content = (
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
    </Group>
  );

  const mainContent =
    href || onClick ? (
      <UnstyledButton
        aria-current={active ? "page" : undefined}
        aria-label={ariaLabel}
        className="vf-sidebar-profile vf-sidebar-profile--interactive"
        component={href ? "a" : "button"}
        href={href}
        onClick={onClick}
        type={href ? undefined : "button"}
      >
        {content}
      </UnstyledButton>
    ) : (
      <Stack className="vf-sidebar-profile" gap="sm">
        {content}
      </Stack>
    );

  if (actionLabel) {
    return (
      <Stack className="vf-sidebar-profile__compound" gap={6}>
        {mainContent}
        <Text
          aria-label={actionAriaLabel}
          className="vf-sidebar-profile__action-link"
          component={actionHref ? "a" : "button"}
          href={actionHref}
          onClick={(event: MouseEvent<HTMLElement>) => {
            event.stopPropagation();
            actionOnClick?.();
          }}
          type={actionHref ? undefined : "button"}
        >
          {actionLabel}
        </Text>
      </Stack>
    );
  }

  return mainContent;
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
