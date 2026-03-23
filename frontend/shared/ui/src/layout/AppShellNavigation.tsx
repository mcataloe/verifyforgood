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
  ariaLabel?: string;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  sections: readonly AppShellNavigationSectionInput[];
}

export function AppShellNavigation({
  activeNavigationKey,
  ariaLabel = "Application navigation",
  onNavigate,
  onNavigationChange,
  sections,
}: AppShellNavigationProps) {
  const visibleSections = sections.filter(
    (section) => section.items.length > 0,
  );

  return (
    <Box aria-label={ariaLabel} className="vf-app-shell-nav" component="nav">
      <Stack gap={verifyForGoodTokens.spacing.baseUnit * 1.5}>
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
    </Box>
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
  const sectionLabelId = `navigation-section-${section.key}`;

  return (
    <Box
      aria-labelledby={sectionLabelId}
      component="section"
      className={
        isFirstSection
          ? "vf-app-shell-nav__section"
          : "vf-app-shell-nav__section vf-app-shell-nav__section--separated"
      }
    >
      <Stack
        gap={6}
        pt={isFirstSection ? 0 : verifyForGoodTokens.spacing.baseUnit * 2}
      >
        <Text
          className="vf-app-shell-nav__section-label"
          component="h2"
          fw={600}
          fz="xs"
          id={sectionLabelId}
          tt="uppercase"
        >
          {section.label}
        </Text>
        {section.helpText ? (
          <Text className="vf-app-shell-nav__section-description" fz="xs">
            {section.helpText}
          </Text>
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
    </Box>
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
        component="button"
        description={depth === 0 ? item.helpText : undefined}
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
        {branchLink}

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
    return (
      <NavLink
        active={isActive}
        aria-current={isSelfActive ? "page" : undefined}
        component="button"
        description={depth === 0 ? item.helpText : undefined}
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
  }

  return (
    <NavLink
      active={isActive}
      aria-current={isSelfActive ? "page" : undefined}
      component="a"
      description={depth === 0 ? item.helpText : undefined}
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
  description: "vf-app-shell-nav__item-description",
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
