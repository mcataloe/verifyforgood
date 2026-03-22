import {
  AppShell as MantineAppShell,
  Box,
  Burger,
  Button,
  Group,
  NavLink,
  ScrollArea,
  Stack,
  Text,
  Title,
} from "@mantine/core";
import { useState, type PropsWithChildren, type ReactNode } from "react";
import { ColorSchemeToggle } from "../components/ColorSchemeToggle";
import type {
  VerifyForGoodNavigationItem,
  VerifyForGoodNavigationSection,
  VerifyForGoodResolvedNavigationItem,
} from "../navigation/schema";
import { verifyForGoodTokens } from "../theme/tokens";
import { useVerifyForGoodColorScheme } from "../components/VerifyForGoodMantineProvider";

export type VerifyForGoodAppShellNavItem = VerifyForGoodNavigationItem;
export type VerifyForGoodAppShellNavSection = VerifyForGoodNavigationSection;

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

export type VerifyForGoodAppShellProps = PropsWithChildren<{
  activeNavigationKey?: string;
  appName?: string;
  contentMaxWidth?: string;
  headerActions?: ReactNode;
  navigation?: readonly VerifyForGoodAppShellNavItem[];
  navigationSections?: readonly VerifyForGoodAppShellNavSection[];
  onNavigationChange?: (item: VerifyForGoodAppShellNavItem) => void;
  sidebarFooter?: ReactNode;
  subtitle?: string;
}>;

const NAVBAR_WIDTH = `calc(${verifyForGoodTokens.spacing.baseUnit}px * 34)`;
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
      header={{ height: HEADER_HEIGHT }}
      navbar={{
        breakpoint: "md",
        collapsed: { desktop: desktopCollapsed, mobile: !mobileOpened },
        width: NAVBAR_WIDTH,
      }}
      padding="lg"
      styles={{
        main: {
          backgroundColor: semantic.background,
          color: semantic.text_primary,
        },
        header: {
          backgroundColor: semantic.surface,
          borderBottom: `1px solid ${semantic.border}`,
        },
        navbar: {
          backgroundColor: semantic.surface,
          borderInlineEnd: `1px solid ${semantic.border}`,
        },
      }}
    >
      <MantineAppShell.Header px="lg">
        <Group h="100%" justify="space-between" wrap="nowrap">
          <Group gap="sm" wrap="nowrap">
            <Burger
              hiddenFrom="md"
              onClick={() => setMobileOpened((current) => !current)}
              opened={mobileOpened}
              size="sm"
            />
            <Burger
              visibleFrom="md"
              onClick={() => setDesktopCollapsed((current) => !current)}
              opened={!desktopCollapsed}
              size="sm"
            />
            <Box>
              <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
                Application Shell
              </Text>
              <Title order={4}>{appName}</Title>
            </Box>
          </Group>

          <Group gap="sm" wrap="nowrap">
            {headerActions}
            <ColorSchemeToggle />
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="md">
        <MantineAppShell.Section>
          <Stack gap="xs">
            <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
              Navigation
            </Text>
            <Title order={3}>{appName}</Title>
            <Text c="dimmed" fz="sm">
              {subtitle}
            </Text>
          </Stack>
        </MantineAppShell.Section>

        <MantineAppShell.Section component={ScrollArea} grow mt="lg">
          <Stack gap="lg">
            {resolvedNavigationSections.map((section) => (
              <Stack gap="xs" key={section.key}>
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
                  {section.items.map((item) =>
                    renderNavigationItem({
                      activeNavigationKey,
                      item,
                      onNavigationChange,
                      onNavigate: () => setMobileOpened(false),
                    }),
                  )}
                </Stack>
              </Stack>
            ))}
          </Stack>
        </MantineAppShell.Section>

        <MantineAppShell.Section mt="md">
          {sidebarFooter ?? (
            <Button fullWidth variant="light">
              Quick Actions
            </Button>
          )}
        </MantineAppShell.Section>
      </MantineAppShell.Navbar>

      <MantineAppShell.Main>
        <Box
          mx="auto"
          px={0}
          style={{
            maxWidth: contentMaxWidth,
            width: "100%",
          }}
        >
          {children}
        </Box>
      </MantineAppShell.Main>
    </MantineAppShell>
  );
}

export function normalizeVerifyForGoodAppShellNavigationSections({
  navigation = verifyForGoodAppShellNavigation,
  navigationSections,
}: {
  navigation?: readonly VerifyForGoodAppShellNavItem[];
  navigationSections?: readonly VerifyForGoodAppShellNavSection[];
}): VerifyForGoodAppShellNavSection[] {
  if (navigationSections) {
    return [...navigationSections];
  }

  return [
    {
      key: "navigation",
      label: "Navigation",
      helpText: "Primary application destinations.",
      items: [...navigation],
    },
  ];
}

function renderNavigationItem({
  activeNavigationKey,
  item,
  onNavigate,
  onNavigationChange,
}: {
  activeNavigationKey?: string;
  item: VerifyForGoodAppShellNavItem | VerifyForGoodResolvedNavigationItem;
  onNavigate: () => void;
  onNavigationChange?: (item: VerifyForGoodAppShellNavItem) => void;
}) {
  const isLocked =
    "visibilityState" in item && item.visibilityState === "locked";
  const hasChildren = Boolean(item.children?.length);

  return (
    <NavLink
      active={item.key === activeNavigationKey}
      aria-current={item.key === activeNavigationKey ? "page" : undefined}
      childrenOffset="md"
      defaultOpened={hasChildren}
      description={item.helpText}
      disabled={isLocked && !hasChildren}
      href={isLocked ? undefined : item.href}
      key={item.key}
      label={item.label}
      leftSection={item.icon}
      onClick={() => {
        onNavigationChange?.(item);
        onNavigate();
      }}
      styles={{
        root: {
          borderRadius: verifyForGoodTokens.radius.input,
        },
      }}
      title={item.helpText}
    >
      {item.children?.map((child) =>
        renderNavigationItem({
          activeNavigationKey,
          item: child,
          onNavigate,
          onNavigationChange,
        }),
      )}
    </NavLink>
  );
}
