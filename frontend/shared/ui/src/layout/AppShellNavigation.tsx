import { Box, NavLink, Stack, Text } from "@mantine/core";
import { useEffect, useState } from "react";
import type {
  VerifyForGoodNavigationItem,
  VerifyForGoodNavigationSection,
  VerifyForGoodResolvedNavigationItem,
  VerifyForGoodResolvedNavigationSection,
} from "../navigation/schema";
import { verifyForGoodTokens } from "../theme/tokens";

type AppShellNavigationSectionInput =
  | VerifyForGoodNavigationSection
  | VerifyForGoodResolvedNavigationSection;

type AppShellNavigationItemInput =
  | VerifyForGoodNavigationItem
  | VerifyForGoodResolvedNavigationItem;

interface AppShellNavigationProps {
  activeNavigationKey?: string;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  sections: readonly AppShellNavigationSectionInput[];
}

export function AppShellNavigation({
  activeNavigationKey,
  onNavigate,
  onNavigationChange,
  sections,
}: AppShellNavigationProps) {
  const visibleSections = sections.filter((section) => section.items.length > 0);

  return (
    <Stack gap="lg">
      {visibleSections.map((section) => (
        <AppShellNavigationSectionView
          activeNavigationKey={activeNavigationKey}
          key={section.key}
          onNavigate={onNavigate}
          onNavigationChange={onNavigationChange}
          section={section}
        />
      ))}
    </Stack>
  );
}

function AppShellNavigationSectionView({
  activeNavigationKey,
  onNavigate,
  onNavigationChange,
  section,
}: {
  activeNavigationKey?: string;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  section: AppShellNavigationSectionInput;
}) {
  return (
    <Stack gap="xs">
      <Box>
        <Text
          c="dimmed"
          fw={500}
          fz="xs"
          title={section.helpText}
          tt="uppercase"
        >
          {section.label}
        </Text>
        {section.helpText ? (
          <Text c="dimmed" fz="xs" mt={2}>
            {section.helpText}
          </Text>
        ) : null}
      </Box>

      <Stack gap="xs">
        {section.items.map((item) => (
          <AppShellNavigationItemView
            activeNavigationKey={activeNavigationKey}
            item={item}
            key={item.key}
            onNavigate={onNavigate}
            onNavigationChange={onNavigationChange}
          />
        ))}
      </Stack>
    </Stack>
  );
}

function AppShellNavigationItemView({
  activeNavigationKey,
  item,
  onNavigate,
  onNavigationChange,
}: {
  activeNavigationKey?: string;
  item: AppShellNavigationItemInput;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
}) {
  const children = item.children ?? [];
  const hasChildren = children.length > 0;
  const isLocked =
    "visibilityState" in item && item.visibilityState === "locked";
  const isSelfActive = item.key === activeNavigationKey;
  const hasActiveDescendant = children.some((child) =>
    hasActiveNavigationItem(child, activeNavigationKey),
  );
  const [opened, setOpened] = useState(() =>
    shouldItemStartOpened(item, activeNavigationKey),
  );

  useEffect(() => {
    if (hasActiveDescendant || children.length <= 1) {
      setOpened(true);
    }
  }, [children.length, hasActiveDescendant]);

  const isActive = isSelfActive || hasActiveDescendant;

  if (hasChildren) {
    return (
      <Box key={item.key}>
        <NavLink
          active={isActive}
          aria-expanded={opened}
          component="button"
          description={item.helpText}
          label={item.label}
          leftSection={item.icon}
          onClick={() => setOpened((current) => !current)}
          rightSection={
            <Box
              component="span"
              style={{
                display: "inline-block",
                transform: opened ? "rotate(90deg)" : "rotate(0deg)",
                transition: "transform 150ms ease",
              }}
            >
              {">"}
            </Box>
          }
          styles={navigationItemStyles}
          title={item.helpText}
          type="button"
        />

        {opened ? (
          <Stack gap="xs" mt="xs" pl="md">
            {children.map((child) => (
              <AppShellNavigationItemView
                activeNavigationKey={activeNavigationKey}
                item={child}
                key={child.key}
                onNavigate={onNavigate}
                onNavigationChange={onNavigationChange}
              />
            ))}
          </Stack>
        ) : null}
      </Box>
    );
  }

  if (isLocked || !item.href) {
    return (
      <NavLink
        active={isActive}
        aria-current={isSelfActive ? "page" : undefined}
        component="button"
        description={item.helpText}
        disabled={isLocked}
        key={item.key}
        label={item.label}
        leftSection={item.icon}
        onClick={() => {
          if (isLocked) {
            return;
          }

          onNavigationChange?.(item);
          onNavigate();
        }}
        styles={navigationItemStyles}
        title={item.helpText}
        type="button"
      />
    );
  }

  return (
    <NavLink
      active={isActive}
      aria-current={isSelfActive ? "page" : undefined}
      component="a"
      description={item.helpText}
      href={item.href}
      key={item.key}
      label={item.label}
      leftSection={item.icon}
      onClick={() => {
        onNavigationChange?.(item);
        onNavigate();
      }}
      styles={navigationItemStyles}
      title={item.helpText}
    />
  );
}

function hasActiveNavigationItem(
  item: AppShellNavigationItemInput,
  activeNavigationKey?: string,
): boolean {
  if (!activeNavigationKey) {
    return false;
  }

  if (item.key === activeNavigationKey) {
    return true;
  }

  return (item.children ?? []).some((child) =>
    hasActiveNavigationItem(child, activeNavigationKey),
  );
}

function shouldItemStartOpened(
  item: AppShellNavigationItemInput,
  activeNavigationKey?: string,
): boolean {
  const children = item.children ?? [];

  if (children.length === 0) {
    return false;
  }

  if (children.length <= 1) {
    return true;
  }

  return children.some((child) =>
    hasActiveNavigationItem(child, activeNavigationKey),
  );
}

const navigationItemStyles = {
  root: {
    borderRadius: verifyForGoodTokens.radius.input,
  },
};
