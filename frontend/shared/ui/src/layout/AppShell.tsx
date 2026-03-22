import {
  ActionIcon,
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
import { verifyForGoodTokens } from "../theme/tokens";
import { useVerifyForGoodColorScheme } from "../components/VerifyForGoodMantineProvider";

export type VerifyForGoodAppShellNavItem = {
  key: string;
  label: string;
  href?: string;
  description?: string;
};

/**
 * Default enterprise navigation scaffold for VerifyForGood application
 * surfaces.
 *
 * Example usage:
 * ```tsx
 * <VerifyForGoodAppShell
 *   activeNavigationKey="dashboard"
 *   appName="VerifyForGood Portal"
 *   navigation={verifyForGoodAppShellNavigation}
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

type VerifyForGoodAppShellProps = PropsWithChildren<{
  activeNavigationKey?: string;
  appName?: string;
  contentMaxWidth?: string;
  headerActions?: ReactNode;
  navigation?: VerifyForGoodAppShellNavItem[];
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
  onNavigationChange,
  sidebarFooter,
  subtitle = "Compliance and CSR operations",
}: VerifyForGoodAppShellProps) {
  const [desktopCollapsed, setDesktopCollapsed] = useState(false);
  const [mobileOpened, setMobileOpened] = useState(false);
  const { resolvedColorScheme, toggleColorScheme } =
    useVerifyForGoodColorScheme();
  const semantic =
    verifyForGoodTokens.color.semantic[
      resolvedColorScheme === "dark" ? "dark" : "light"
    ];

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
            <ActionIcon
              aria-label="Toggle light and dark theme"
              onClick={toggleColorScheme}
              radius="xl"
              size="lg"
              variant="light"
            >
              <Text fz="sm" fw={700}>
                {resolvedColorScheme === "dark" ? "D" : "L"}
              </Text>
            </ActionIcon>
          </Group>
        </Group>
      </MantineAppShell.Header>

      <MantineAppShell.Navbar p="md">
        <MantineAppShell.Section>
          <Stack gap="xs">
            <Text c="dimmed" fw={500} fz="xs" tt="uppercase">
              Workspace
            </Text>
            <Title order={3}>{appName}</Title>
            <Text c="dimmed" fz="sm">
              {subtitle}
            </Text>
          </Stack>
        </MantineAppShell.Section>

        <MantineAppShell.Section component={ScrollArea} grow mt="lg">
          <Stack gap="xs">
            {navigation.map((item) => (
              <NavLink
                active={item.key === activeNavigationKey}
                aria-current={
                  item.key === activeNavigationKey ? "page" : undefined
                }
                description={item.description}
                href={item.href}
                key={item.key}
                label={item.label}
                onClick={() => {
                  onNavigationChange?.(item);
                  setMobileOpened(false);
                }}
                styles={{
                  root: {
                    borderRadius: verifyForGoodTokens.radius.input,
                  },
                }}
              />
            ))}
          </Stack>
        </MantineAppShell.Section>

        <MantineAppShell.Section mt="md">
          {sidebarFooter ?? (
            <Button fullWidth variant="light">
              Workspace Actions
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
