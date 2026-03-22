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
    <Stack gap={verifyForGoodTokens.spacing.baseUnit}>
      {visibleSections.map((section, index) => (
        <AppShellNavigationSectionView
          activeNavigationKey={activeNavigationKey}
          isFirstSection={index === 0}
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
  isFirstSection,
  onNavigate,
  onNavigationChange,
  section,
}: {
  activeNavigationKey?: string;
  isFirstSection: boolean;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  section: AppShellNavigationSectionInput;
}) {
  const sectionHelpDescriptionId = section.helpText
    ? `navigation-section-help-${section.key}`
    : undefined;

  return (
    <Stack
      className={
        isFirstSection
          ? "vf-app-shell-nav__section"
          : "vf-app-shell-nav__section vf-app-shell-nav__section--separated"
      }
      gap={6}
      pt={isFirstSection ? 0 : verifyForGoodTokens.spacing.baseUnit * 2}
    >
      <Group
        align="center"
        className="vf-app-shell-nav__section-header"
        gap={6}
        justify="space-between"
        wrap="nowrap"
      >
        <Text className="vf-app-shell-nav__section-label" fw={500} fz="xs" tt="uppercase">
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
              className="vf-app-shell-nav__section-help"
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

      <Stack gap={4}>
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
  depth = 0,
  item,
  onNavigate,
  onNavigationChange,
}: {
  activeNavigationKey?: string;
  depth?: number;
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
            className={
              opened
                ? "vf-app-shell-nav__item-chevron vf-app-shell-nav__item-chevron--opened"
                : "vf-app-shell-nav__item-chevron"
            }
            component="span"
          >
            {">"}
          </Box>
        }
        className={getNavigationItemClassName({
          depth,
          hasChildren: true,
          isExpanded: opened,
        })}
        classNames={navigationItemClassNames}
        type="button"
      />
    );

    return (
      <Box key={item.key}>
        {withNavigationHelpTooltip(branchLink, item.helpText, helpDescriptionId)}

        {opened ? (
          <Stack
            className="vf-app-shell-nav__children"
            gap={4}
            mt={4}
            ml={10}
            pl={verifyForGoodTokens.spacing.baseUnit + 2}
          >
            {children.map((child) => (
              <AppShellNavigationItemView
                activeNavigationKey={activeNavigationKey}
                depth={depth + 1}
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
            <Text
              className="vf-app-shell-nav__lock-pill"
              component="span"
              fw={600}
              fz={10}
            >
              Locked
            </Text>
          ) : undefined
        }
        className={getNavigationItemClassName({
          depth,
          hasChildren: false,
          isLocked,
        })}
        classNames={navigationItemClassNames}
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
      className={getNavigationItemClassName({
        depth,
        hasChildren: false,
      })}
      classNames={navigationItemClassNames}
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

const navigationItemClassNames = {
  body: "vf-app-shell-nav__item-body",
  label: "vf-app-shell-nav__item-label",
  section: "vf-app-shell-nav__item-section",
};

function getNavigationItemClassName({
  depth,
  hasChildren,
  isExpanded = false,
  isLocked = false,
}: {
  depth: number;
  hasChildren: boolean;
  isExpanded?: boolean;
  isLocked?: boolean;
}) {
  return [
    "vf-app-shell-nav__item",
    depth > 0 ? "vf-app-shell-nav__item--child" : undefined,
    hasChildren ? "vf-app-shell-nav__item--branch" : undefined,
    isExpanded ? "vf-app-shell-nav__item--expanded" : undefined,
    isLocked ? "vf-app-shell-nav__item--locked" : undefined,
  ]
    .filter(Boolean)
    .join(" ");
}

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
