import { Box, NavLink, Stack, Text, Tooltip, VisuallyHidden } from "@mantine/core";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
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
  collapsed?: boolean;
  onExpandSidebar?: () => void;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  sections: readonly AppShellNavigationSectionInput[];
}

export function AppShellNavigation({
  activeNavigationKey,
  ariaLabel = "Application navigation",
  collapsed = false,
  onExpandSidebar,
  onNavigate,
  onNavigationChange,
  sections,
}: AppShellNavigationProps) {
  const visibleSections = useMemo(
    () => sections.filter((section) => section.items.length > 0),
    [sections],
  );
  const [openedTopLevelBranchKey, setOpenedTopLevelBranchKey] = useState<
    string | null
  >(() => resolveInitialTopLevelBranchKey(visibleSections, activeNavigationKey));
  const previousActiveNavigationKeyRef = useRef(activeNavigationKey);

  useEffect(() => {
    const activeBranchKey = resolveInitialTopLevelBranchKey(
      visibleSections,
      activeNavigationKey,
    );
    const activeNavigationChanged =
      previousActiveNavigationKeyRef.current !== activeNavigationKey;
    previousActiveNavigationKeyRef.current = activeNavigationKey;

    setOpenedTopLevelBranchKey((current) => {
      if (activeNavigationChanged) {
        return activeBranchKey;
      }

      if (
        current &&
        topLevelBranchExists(visibleSections, current)
      ) {
        return current;
      }

      return activeBranchKey;
    });
  }, [activeNavigationKey, visibleSections]);

  return (
    <Box aria-label={ariaLabel} className="vf-app-shell-nav" component="nav">
      <Stack gap={verifyForGoodTokens.spacing.baseUnit * 1.5}>
        {visibleSections.map((section, index) => (
          <AppShellNavigationSectionView
            activeNavigationKey={activeNavigationKey}
            collapsed={collapsed}
            isFirstSection={index === 0}
            key={section.key}
            onExpandSidebar={onExpandSidebar}
            onNavigate={onNavigate}
            onNavigationChange={onNavigationChange}
            onToggleTopLevelBranch={(branchKey) => {
              setOpenedTopLevelBranchKey((current) =>
                current === branchKey ? null : branchKey,
              );
            }}
            openedTopLevelBranchKey={openedTopLevelBranchKey}
            section={section}
          />
        ))}
      </Stack>
    </Box>
  );
}

function AppShellNavigationSectionView({
  activeNavigationKey,
  collapsed,
  isFirstSection,
  onExpandSidebar,
  onNavigate,
  onNavigationChange,
  onToggleTopLevelBranch,
  openedTopLevelBranchKey,
  section,
}: {
  activeNavigationKey?: string;
  collapsed: boolean;
  isFirstSection: boolean;
  onExpandSidebar?: () => void;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  onToggleTopLevelBranch: (branchKey: string) => void;
  openedTopLevelBranchKey: string | null;
  section: AppShellNavigationSectionInput;
}) {
  const sectionLabelId = `navigation-section-${section.key}`;

  return (
    <Box
      aria-label={section.label || "Navigation group"}
      aria-labelledby={section.label ? sectionLabelId : undefined}
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
        {!collapsed && (section.label || section.helpText) ? (
          <Box className="vf-app-shell-nav__section-heading">
            <SectionTooltipWrapper
              helpText={section.helpText}
              label={section.label || "Section"}
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
            </SectionTooltipWrapper>
          </Box>
        ) : null}

        <Stack gap={4}>
          {section.items.map((item) => (
            <AppShellNavigationItemView
              activeNavigationKey={activeNavigationKey}
              collapsed={collapsed}
              item={item}
              key={item.key}
              onExpandSidebar={onExpandSidebar}
              onNavigate={onNavigate}
              onNavigationChange={onNavigationChange}
              onToggleTopLevelBranch={onToggleTopLevelBranch}
              openedTopLevelBranchKey={openedTopLevelBranchKey}
            />
          ))}
        </Stack>
      </Stack>
    </Box>
  );
}

function AppShellNavigationItemView({
  activeNavigationKey,
  collapsed = false,
  depth = 0,
  item,
  onExpandSidebar,
  onNavigate,
  onNavigationChange,
  onToggleTopLevelBranch,
  openedTopLevelBranchKey,
}: {
  activeNavigationKey?: string;
  collapsed?: boolean;
  depth?: number;
  item: AppShellNavigationItemInput;
  onExpandSidebar?: () => void;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodNavigationItem) => void;
  onToggleTopLevelBranch: (branchKey: string) => void;
  openedTopLevelBranchKey: string | null;
}) {
  const isRailItem = collapsed && depth === 0;
  const children = item.children ?? [];
  const hasChildren = children.length > 0;
  const isLocked =
    "visibilityState" in item && item.visibilityState === "locked";
  const isSelfActive = item.key === activeNavigationKey;
  const hasActiveDescendant = children.some((child) =>
    hasActiveNavigationItem(child, activeNavigationKey),
  );
  const [opened, setOpened] = useState(() =>
    depth === 0
      ? openedTopLevelBranchKey === item.key
      : shouldItemStartOpened(item, activeNavigationKey),
  );
  const helpTextId = `${item.key}-navigation-help`;

  useEffect(() => {
    if (depth === 0) {
      return;
    }

    if (hasActiveDescendant || children.length <= 1) {
      setOpened(true);
    }
  }, [children.length, depth, hasActiveDescendant]);

  const isActive = isSelfActive || hasActiveDescendant;
  const isTopLevelBranch = depth === 0 && hasChildren;
  const isOpened = isTopLevelBranch ? openedTopLevelBranchKey === item.key : opened;

  if (hasChildren) {
    const branchLink = (
      <NavLink
        active={isActive}
        aria-expanded={isOpened}
        aria-describedby={item.helpText ? helpTextId : undefined}
        aria-label={isRailItem ? item.label : undefined}
        component="button"
        label={isRailItem ? undefined : item.label}
        leftSection={item.icon}
        onClick={() => {
          if (isTopLevelBranch) {
            if (collapsed) {
              onExpandSidebar?.();
            }
            onToggleTopLevelBranch(item.key);
            return;
          }

          setOpened((current) => !current);
        }}
        rightSection={
          isRailItem ? undefined : (
            <Box
              aria-hidden="true"
              className={
                isOpened
                  ? "vf-app-shell-nav__item-chevron vf-app-shell-nav__item-chevron--opened"
                  : "vf-app-shell-nav__item-chevron"
              }
              component="span"
            >
              {">"}
            </Box>
          )
        }
        className={getNavigationItemClassName({
          depth,
          hasChildren: true,
          isExpanded: isOpened,
          isRailItem,
        })}
        classNames={navigationItemClassNames}
        type="button"
      />
    );

    return (
      <Box key={item.key}>
        <NavigationTooltipWrapper
          forceLabel={isRailItem ? item.label : undefined}
          helpText={item.helpText}
        >
          {branchLink}
        </NavigationTooltipWrapper>
        {item.helpText ? (
          <VisuallyHidden id={helpTextId}>{item.helpText}</VisuallyHidden>
        ) : null}

        {isOpened && !collapsed ? (
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
                onToggleTopLevelBranch={onToggleTopLevelBranch}
                openedTopLevelBranchKey={openedTopLevelBranchKey}
              />
            ))}
          </Stack>
        ) : null}
      </Box>
    );
  }

  if (isLocked || !item.href) {
    return (
      <ItemWithTooltip
        forceLabel={isRailItem ? item.label : undefined}
        helpText={item.helpText}
        helpTextId={helpTextId}
      >
        <NavLink
          active={isActive}
          aria-current={isSelfActive ? "page" : undefined}
          aria-describedby={item.helpText ? helpTextId : undefined}
          aria-label={isRailItem ? item.label : undefined}
          component="button"
          disabled={isLocked}
          key={item.key}
          label={isRailItem ? undefined : item.label}
          leftSection={item.icon}
          onClick={() => {
            if (isLocked) {
              return;
            }

            onNavigationChange?.(item);
            onNavigate();
          }}
          rightSection={
            isLocked && !isRailItem ? (
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
            isRailItem,
          })}
          classNames={navigationItemClassNames}
          type="button"
        />
      </ItemWithTooltip>
    );
  }

  return (
    <ItemWithTooltip
      forceLabel={isRailItem ? item.label : undefined}
      helpText={item.helpText}
      helpTextId={helpTextId}
    >
      <NavLink
        active={isActive}
        aria-current={isSelfActive ? "page" : undefined}
        aria-describedby={item.helpText ? helpTextId : undefined}
        aria-label={isRailItem ? item.label : undefined}
        component="a"
        href={item.href}
        key={item.key}
        label={isRailItem ? undefined : item.label}
        leftSection={item.icon}
        onClick={() => {
          onNavigationChange?.(item);
          onNavigate();
        }}
        className={getNavigationItemClassName({
          depth,
          hasChildren: false,
          isRailItem,
        })}
        classNames={navigationItemClassNames}
      />
    </ItemWithTooltip>
  );
}

function resolveInitialTopLevelBranchKey(
  sections: readonly AppShellNavigationSectionInput[],
  activeNavigationKey?: string,
) {
  for (const section of sections) {
    for (const item of section.items) {
      if (
        (item.children ?? []).length > 0 &&
        hasActiveNavigationItem(item, activeNavigationKey)
      ) {
        return item.key;
      }
    }
  }

  for (const section of sections) {
    for (const item of section.items) {
      if ((item.children ?? []).length <= 1 && (item.children ?? []).length > 0) {
        return item.key;
      }
    }
  }

  return null;
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

function topLevelBranchExists(
  sections: readonly AppShellNavigationSectionInput[],
  branchKey: string,
) {
  return sections.some((section) =>
    section.items.some(
      (item) => item.key === branchKey && (item.children ?? []).length > 0,
    ),
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
  isRailItem = false,
}: {
  depth: number;
  hasChildren: boolean;
  isExpanded?: boolean;
  isLocked?: boolean;
  isRailItem?: boolean;
}) {
  return [
    "vf-app-shell-nav__item",
    depth > 0 ? "vf-app-shell-nav__item--child" : undefined,
    hasChildren ? "vf-app-shell-nav__item--branch" : undefined,
    isExpanded ? "vf-app-shell-nav__item--expanded" : undefined,
    isLocked ? "vf-app-shell-nav__item--locked" : undefined,
    isRailItem ? "vf-app-shell-nav__item--rail" : undefined,
  ]
    .filter(Boolean)
    .join(" ");
}

function ItemWithTooltip({
  children,
  forceLabel,
  helpText,
  helpTextId,
}: {
  children: ReactNode;
  forceLabel?: string;
  helpText?: string;
  helpTextId: string;
}) {
  return (
    <>
      <NavigationTooltipWrapper forceLabel={forceLabel} helpText={helpText}>
        {children}
      </NavigationTooltipWrapper>
      {helpText ? <VisuallyHidden id={helpTextId}>{helpText}</VisuallyHidden> : null}
    </>
  );
}

function NavigationTooltipWrapper({
  children,
  forceLabel,
  helpText,
}: {
  children: ReactNode;
  forceLabel?: string;
  helpText?: string;
}) {
  const label = forceLabel || helpText;
  if (!label) {
    return <>{children}</>;
  }

  return (
    <Tooltip
      label={label}
      multiline
      openDelay={120}
      position={forceLabel ? "right" : undefined}
      withArrow
      withinPortal={Boolean(forceLabel)}
    >
      <Box>{children}</Box>
    </Tooltip>
  );
}

function SectionTooltipWrapper({
  children,
  helpText,
  label,
}: {
  children: ReactNode;
  helpText?: string;
  label: string;
}) {
  if (!helpText) {
    return <>{children}</>;
  }

  return (
    <Tooltip
      label={helpText}
      multiline
      openDelay={120}
      withArrow
      withinPortal={false}
    >
      <Box
        aria-label={`${label} section details`}
        className="vf-app-shell-nav__section-tooltip-target"
        component="span"
        tabIndex={0}
      >
        {children}
      </Box>
    </Tooltip>
  );
}
