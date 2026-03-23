import { Box, NavLink, Stack, Text, Tooltip, VisuallyHidden } from "@mantine/core";
import { useEffect, useState, type ReactNode } from "react";
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
        {section.label || section.helpText ? (
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
  const helpTextId = `${item.key}-navigation-help`;

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
        aria-describedby={item.helpText ? helpTextId : undefined}
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
        <NavigationTooltipWrapper helpText={item.helpText}>
          {branchLink}
        </NavigationTooltipWrapper>
        {item.helpText ? (
          <VisuallyHidden id={helpTextId}>{item.helpText}</VisuallyHidden>
        ) : null}

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
      <ItemWithTooltip helpText={item.helpText} helpTextId={helpTextId}>
        <NavLink
          active={isActive}
          aria-current={isSelfActive ? "page" : undefined}
          aria-describedby={item.helpText ? helpTextId : undefined}
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
      </ItemWithTooltip>
    );
  }

  return (
    <ItemWithTooltip helpText={item.helpText} helpTextId={helpTextId}>
      <NavLink
        active={isActive}
        aria-current={isSelfActive ? "page" : undefined}
        aria-describedby={item.helpText ? helpTextId : undefined}
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
    </ItemWithTooltip>
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

function ItemWithTooltip({
  children,
  helpText,
  helpTextId,
}: {
  children: ReactNode;
  helpText?: string;
  helpTextId: string;
}) {
  return (
    <>
      <NavigationTooltipWrapper helpText={helpText}>{children}</NavigationTooltipWrapper>
      {helpText ? <VisuallyHidden id={helpTextId}>{helpText}</VisuallyHidden> : null}
    </>
  );
}

function NavigationTooltipWrapper({
  children,
  helpText,
}: {
  children: ReactNode;
  helpText?: string;
}) {
  if (!helpText) {
    return <>{children}</>;
  }

  return (
    <Tooltip label={helpText} multiline openDelay={120} withArrow withinPortal={false}>
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
