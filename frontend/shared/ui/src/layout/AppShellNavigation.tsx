import {
  ActionIcon,
  Box,
  Group,
  NavLink,
  Stack,
  Text,
  Tooltip,
  VisuallyHidden,
} from "@mantine/core";
import { useEffect, useState, type ReactElement, type ReactNode } from "react";
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
  const sectionHelpDescriptionId = section.helpText
    ? `navigation-section-help-${section.key}`
    : undefined;

  return (
    <Stack gap="xs">
      <Group align="center" gap={4} wrap="nowrap">
        <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
          {section.label}
        </Text>
        {section.helpText ? (
          <Tooltip
            events={{ focus: true, hover: true, touch: false }}
            label={section.helpText}
            maw={280}
            multiline
            position="right"
            withinPortal={false}
          >
            <ActionIcon
              aria-label={`About ${section.label}`}
              aria-describedby={sectionHelpDescriptionId}
              color="gray"
              radius="xl"
              size="xs"
              variant="subtle"
            >
              <Text component="span" fw={700} fz={10}>
                i
              </Text>
            </ActionIcon>
          </Tooltip>
        ) : null}
      </Group>
      {section.helpText && sectionHelpDescriptionId ? (
        <VisuallyHidden id={sectionHelpDescriptionId}>
          {section.helpText}
        </VisuallyHidden>
      ) : null}

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
  const helpDescriptionId = item.helpText
    ? `navigation-item-help-${item.key}`
    : undefined;
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
    const branchLink = (
      <NavLink
        active={isActive}
        aria-expanded={opened}
        aria-describedby={helpDescriptionId}
        component="button"
        label={item.label}
        leftSection={item.icon}
        onClick={() => setOpened((current) => !current)}
        rightSection={
          <Box
            aria-hidden="true"
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
        type="button"
      />
    );

    return (
      <Box key={item.key}>
        {withNavigationHelpTooltip(branchLink, item.helpText, helpDescriptionId)}

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
    const lockedOrUnavailableLink = (
      <NavLink
        active={isActive}
        aria-current={isSelfActive ? "page" : undefined}
        aria-describedby={helpDescriptionId}
        component="button"
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
        rightSection={
          isLocked ? (
            <Text component="span" c="dimmed" fw={600} fz="xs">
              Locked
            </Text>
          ) : undefined
        }
        styles={navigationItemStyles}
        type="button"
      />
    );

    return withNavigationHelpTooltip(
      lockedOrUnavailableLink,
      item.helpText,
      helpDescriptionId,
    );
  }

  const link = (
    <NavLink
      active={isActive}
      aria-current={isSelfActive ? "page" : undefined}
      aria-describedby={helpDescriptionId}
      component="a"
      href={item.href}
      key={item.key}
      label={item.label}
      leftSection={item.icon}
      onClick={() => {
        onNavigationChange?.(item);
        onNavigate();
      }}
      styles={navigationItemStyles}
    />
  );

  return withNavigationHelpTooltip(link, item.helpText, helpDescriptionId);
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

function withNavigationHelpTooltip(
  node: ReactElement,
  helpText?: string,
  helpDescriptionId?: string,
): ReactNode {
  if (!helpText) {
    return node;
  }

  return (
    <>
      <Tooltip
        events={{ focus: true, hover: true, touch: false }}
        label={helpText}
        maw={320}
        multiline
        position="right"
        withinPortal={false}
      >
        {node}
      </Tooltip>
      {helpDescriptionId ? (
        <VisuallyHidden id={helpDescriptionId}>{helpText}</VisuallyHidden>
      ) : null}
    </>
  );
}
