import {
  ActionIcon,
  AppShell as MantineAppShell,
  Box,
  Group,
  Menu,
  ScrollArea,
  Stack,
  Text,
  Title,
  Tooltip,
  UnstyledButton,
} from "@mantine/core";
import {
  IconHelpCircle,
  IconLayoutSidebarLeftCollapse,
  IconLayoutSidebarLeftExpand,
  IconRocket,
} from "@tabler/icons-react";
import { useState, type PropsWithChildren, type ReactNode } from "react";
import type {
  VerifyForGoodNavigationItem,
  VerifyForGoodNavigationSection,
  VerifyForGoodResolvedNavigationItem,
  VerifyForGoodResolvedNavigationSection,
} from "../navigation/schema";
import { verifyForGoodTokens } from "../theme/tokens";
import { useVerifyForGoodColorScheme } from "../components/VerifyForGoodMantineProvider";
import { AppShellNavigation } from "./AppShellNavigation";

export type VerifyForGoodAppShellNavItem =
  | VerifyForGoodNavigationItem
  | VerifyForGoodResolvedNavigationItem;
export type VerifyForGoodAppShellNavSection =
  | VerifyForGoodNavigationSection
  | VerifyForGoodResolvedNavigationSection;

/**
 * Default enterprise navigation scaffold for VerifyForGood application
 * surfaces.
 *
 * Example usage:
 * ```tsx
 * <VerifyForGoodAppShell
 *   activeNavigationKey="dashboard"
 *   appName="VerifyForGood Portal"
 *   navigationSections={verifyForGoodAppShellNavigationSections}
 *   onNavigationChange={(item) => console.log(item.key)}
 * >
 *   <DashboardPage />
 * </VerifyForGoodAppShell>
 * ```
 */
export const verifyForGoodAppShellNavigation: VerifyForGoodAppShellNavItem[] = [
  { key: "dashboard", label: "Dashboard", href: "#dashboard" },
  { key: "organizations", label: "Organizations", href: "#organizations" },
  { key: "verifications", label: "Verifications", href: "#verifications" },
  { key: "reports", label: "Reports", href: "#reports" },
  { key: "api-keys", label: "API Keys", href: "#api-keys" },
  { key: "billing", label: "Billing", href: "#billing" },
  { key: "settings", label: "Settings", href: "#settings" },
];

export const verifyForGoodAppShellNavigationSections: VerifyForGoodNavigationSection[] =
  [
    {
      key: "navigation",
      label: "Navigation",
      helpText: "Default application shell navigation.",
      items: verifyForGoodAppShellNavigation,
    },
  ];

export type VerifyForGoodAppShellSidebarHelpItem = {
  href: string;
  key: string;
  label: string;
};

export type VerifyForGoodAppShellProps = PropsWithChildren<{
  activeNavigationKey?: string;
  appName?: string;
  contentMaxWidth?: string;
  headerActions?: ReactNode;
  navigation?: readonly VerifyForGoodAppShellNavItem[];
  navigationSections?: readonly VerifyForGoodAppShellNavSection[];
  onNavigationChange?: (item: VerifyForGoodAppShellNavItem) => void;
  sidebarFooter?: ReactNode;
  sidebarHelpItems?: readonly VerifyForGoodAppShellSidebarHelpItem[];
  sidebarUpgradeHref?: string;
  showHeader?: boolean;
  showSidebarHeader?: boolean;
  sidebarNavigationAriaLabel?: string;
  sidebarSummary?: ReactNode;
  subtitle?: string;
}>;

const NAVBAR_WIDTH = `calc(${verifyForGoodTokens.spacing.baseUnit}px * 34)`;
const NAVBAR_COLLAPSED_WIDTH = `calc(${verifyForGoodTokens.spacing.baseUnit}px * 8)`;
const HEADER_HEIGHT = `calc(${verifyForGoodTokens.spacing.baseUnit}px * 9)`;
const CONTENT_MAX_WIDTH = `calc(${verifyForGoodTokens.spacing.baseUnit}px * 160)`;

export function VerifyForGoodAppShell({
  activeNavigationKey = "dashboard",
  appName = "VerifyForGood",
  children,
  contentMaxWidth = CONTENT_MAX_WIDTH,
  headerActions,
  navigation = verifyForGoodAppShellNavigation,
  navigationSections,
  onNavigationChange,
  sidebarFooter,
  sidebarHelpItems,
  sidebarUpgradeHref,
  showHeader = true,
  showSidebarHeader = true,
  sidebarNavigationAriaLabel = "Application navigation",
  sidebarSummary,
  subtitle = "Compliance and CSR operations",
}: VerifyForGoodAppShellProps) {
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [mobileOpened, setMobileOpened] = useState(false);
  const { resolvedColorScheme } = useVerifyForGoodColorScheme();
  const semantic =
    verifyForGoodTokens.color.semantic[
      resolvedColorScheme === "dark" ? "dark" : "light"
    ];
  const resolvedNavigationSections =
    normalizeVerifyForGoodAppShellNavigationSections({
      navigation,
      navigationSections,
    });

  return (
    <MantineAppShell
      header={showHeader ? { height: HEADER_HEIGHT } : undefined}
      navbar={{
        breakpoint: "md",
        collapsed: { desktop: false, mobile: !mobileOpened },
        width: desktopCollapsed ? NAVBAR_COLLAPSED_WIDTH : NAVBAR_WIDTH,
      }}
      padding="lg"
      styles={{
        root: {
          minHeight: "100vh",
        },
        main: {
          backgroundColor: semantic.background,
          color: semantic.text_primary,
          minHeight: showHeader ? `calc(100vh - ${HEADER_HEIGHT})` : "100vh",
          overflowY: "auto",
        },
        header: {
          backgroundColor: semantic.surface,
          borderBottom: `1px solid ${semantic.border}`,
        },
        navbar: {
          backgroundColor: semantic.surface,
          borderInlineEnd: `1px solid ${semantic.border}`,
          transition: "width 150ms ease",
        },
      }}
    >
      {showHeader ? (
        <MantineAppShell.Header px="lg">
          <Group h="100%" justify="space-between" wrap="nowrap">
            <Group gap="sm" wrap="nowrap">
              <ActionIcon
                hiddenFrom="md"
                aria-label={mobileOpened ? "Collapse sidebar" : "Expand sidebar"}
                onClick={() => setMobileOpened((current) => !current)}
                size="sm"
                variant="subtle"
              >
                {mobileOpened ? (
                  <IconLayoutSidebarLeftCollapse
                    aria-hidden="true"
                    size={18}
                    stroke={1.8}
                  />
                ) : (
                  <IconLayoutSidebarLeftExpand
                    aria-hidden="true"
                    size={18}
                    stroke={1.8}
                  />
                )}
              </ActionIcon>
              <Box>
                <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
                  Application Shell
                </Text>
                <Title order={4}>{appName}</Title>
              </Box>
            </Group>

            <Group gap="sm" wrap="nowrap">
              {headerActions}
            </Group>
          </Group>
        </MantineAppShell.Header>
      ) : null}

      <MantineAppShell.Navbar
        className={
          desktopCollapsed
            ? "vf-app-shell-sidebar vf-app-shell-sidebar--collapsed"
            : "vf-app-shell-sidebar"
        }
        p={0}
      >
        {showSidebarHeader ? (
          <MantineAppShell.Section
            className="vf-app-shell-sidebar__header"
            data-testid="vf-app-shell-sidebar-header"
          >
            <Box className="vf-app-shell-sidebar__header-inner">
              <Group
                align="flex-start"
                className="vf-app-shell-sidebar__brand"
                gap="sm"
                wrap="nowrap"
              >
                <Box
                  aria-hidden="true"
                  className="vf-app-shell-sidebar__brand-mark"
                >
                  {getAppShellBrandMark(appName)}
                </Box>
                <Box className="vf-app-shell-sidebar__brand-copy">
                  <Text
                    className="vf-app-shell-sidebar__header-eyebrow"
                    fw={500}
                    fz="xs"
                    tt="uppercase"
                  >
                    Application
                  </Text>
                  <Text className="vf-app-shell-sidebar__header-title" fw={700}>
                    {appName}
                  </Text>
                  {subtitle ? (
                    <Text
                      className="vf-app-shell-sidebar__header-subtitle"
                      fz="sm"
                    >
                      {subtitle}
                    </Text>
                  ) : null}
                </Box>
              </Group>
              {sidebarSummary ? (
                <Box
                  className="vf-app-shell-sidebar__header-summary"
                  data-testid="vf-app-shell-sidebar-summary"
                >
                  {sidebarSummary}
                </Box>
              ) : null}
            </Box>
          </MantineAppShell.Section>
        ) : null}

        <MantineAppShell.Section
          className="vf-app-shell-sidebar__content"
          component={ScrollArea}
          data-testid="vf-app-shell-sidebar-content"
          grow
        >
          <Box className="vf-app-shell-sidebar__content-inner">
            <AppShellNavigation
              activeNavigationKey={activeNavigationKey}
              ariaLabel={sidebarNavigationAriaLabel}
              collapsed={desktopCollapsed}
              onExpandSidebar={() => setDesktopCollapsed(false)}
              onNavigate={() => setMobileOpened(false)}
              onNavigationChange={onNavigationChange}
              sections={resolvedNavigationSections}
            />
          </Box>
        </MantineAppShell.Section>

        <MantineAppShell.Section
          className="vf-app-shell-sidebar__footer"
          data-testid="vf-app-shell-sidebar-footer"
        >
          <Box className="vf-app-shell-sidebar__footer-inner">
            {sidebarFooter}
            <AppShellSidebarUtilityNav
              collapsed={desktopCollapsed}
              helpItems={sidebarHelpItems}
              onToggleCollapsed={() => setDesktopCollapsed((current) => !current)}
              upgradeHref={sidebarUpgradeHref}
            />
          </Box>
        </MantineAppShell.Section>
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>
        <Box
          className="vf-app-shell-main__content"
          mx="auto"
          px={0}
          style={{
            maxWidth: contentMaxWidth,
            minWidth: 0,
            width: "100%",
          }}
        >
          {children}
        </Box>
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}

function AppShellSidebarUtilityNav({
  collapsed,
  helpItems,
  onToggleCollapsed,
  upgradeHref,
}: {
  collapsed: boolean;
  helpItems?: readonly VerifyForGoodAppShellSidebarHelpItem[];
  onToggleCollapsed: () => void;
  upgradeHref?: string;
}) {
  const [helpOpened, setHelpOpened] = useState(false);
  const iconSize = 20;

  return (
    <Stack className="vf-sidebar-utility" gap={2} visibleFrom="md">
      {upgradeHref ? (
        <UtilityNavTooltip collapsed={collapsed} label="Upgrade subscription">
          <UnstyledButton
            className="vf-sidebar-utility__item"
            component="a"
            href={upgradeHref}
          >
            <Group gap="sm" wrap="nowrap">
              <IconRocket aria-hidden="true" size={iconSize} stroke={1.8} />
              {collapsed ? null : <Text fz="sm">Upgrade subscription</Text>}
            </Group>
          </UnstyledButton>
        </UtilityNavTooltip>
      ) : null}

      {helpItems && helpItems.length > 0 ? (
        <Menu
          keepMounted
          onChange={setHelpOpened}
          opened={helpOpened}
          position={collapsed ? "right-end" : "top-start"}
          shadow="md"
          width={260}
        >
          <Menu.Target>
            <UtilityNavTooltip collapsed={collapsed} label="Help">
              <UnstyledButton
                aria-expanded={helpOpened}
                className="vf-sidebar-utility__item"
              >
                <Group gap="sm" wrap="nowrap">
                  <IconHelpCircle aria-hidden="true" size={iconSize} stroke={1.8} />
                  {collapsed ? null : <Text fz="sm">Help</Text>}
                </Group>
              </UnstyledButton>
            </UtilityNavTooltip>
          </Menu.Target>
          <Menu.Dropdown>
            {helpItems.map((item) => (
              <Menu.Item
                component="a"
                data-testid={`vf-sidebar-help-item-${item.key}`}
                href={item.href}
                key={item.key}
              >
                {item.label}
              </Menu.Item>
            ))}
          </Menu.Dropdown>
        </Menu>
      ) : null}

      <UtilityNavTooltip
        collapsed={collapsed}
        label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
      >
        <UnstyledButton
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="vf-sidebar-utility__item"
          onClick={onToggleCollapsed}
        >
          <Group gap="sm" wrap="nowrap">
            {collapsed ? (
              <IconLayoutSidebarLeftExpand
                aria-hidden="true"
                size={iconSize}
                stroke={1.8}
              />
            ) : (
              <IconLayoutSidebarLeftCollapse
                aria-hidden="true"
                size={iconSize}
                stroke={1.8}
              />
            )}
            {collapsed ? null : (
              <Text fz="sm">{collapsed ? "Expand sidebar" : "Collapse sidebar"}</Text>
            )}
          </Group>
        </UnstyledButton>
      </UtilityNavTooltip>
    </Stack>
  );
}

function UtilityNavTooltip({
  children,
  collapsed,
  label,
}: {
  children: ReactNode;
  collapsed: boolean;
  label: string;
}) {
  if (!collapsed) {
    return <>{children}</>;
  }

  return (
    <Tooltip label={label} position="right" withArrow withinPortal>
      <Box>{children}</Box>
    </Tooltip>
  );
}

function getAppShellBrandMark(appName: string) {
  const initials = appName
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("");

  return initials || "VF";
}

export function normalizeVerifyForGoodAppShellNavigationSections({
  navigation = verifyForGoodAppShellNavigation,
  navigationSections,
}: {
  navigation?: readonly VerifyForGoodAppShellNavItem[];
  navigationSections?: readonly VerifyForGoodAppShellNavSection[];
}): VerifyForGoodAppShellNavSection[] {
  if (navigationSections) {
    return [...navigationSections].filter(
      (section) => section.items.length > 0,
    );
  }

  return [
    {
      key: "navigation",
      label: "Navigation",
      helpText: "Primary application destinations.",
      items: [...navigation],
    },
  ].filter((section) => section.items.length > 0);
}
