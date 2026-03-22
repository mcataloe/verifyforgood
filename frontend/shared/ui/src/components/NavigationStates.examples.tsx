import { Button, Group, Stack, Tabs, Text } from "@mantine/core";
import {
  FRONTEND_ACCESS_ROLE,
  type FrontendAccessRole,
  type PlanCode,
} from "@charity-status/shared-types";
import { useEffect, useMemo, useState } from "react";
import { Card } from "./Card";
import { VerifyForGoodMantineProvider } from "./VerifyForGoodMantineProvider";
import { useVerifyForGoodColorScheme } from "./VerifyForGoodMantineProvider";
import { VerifyForGoodAppShell } from "../layout/AppShell";
import { filterNavigationSections } from "../navigation/filterNavigation";
import type {
  VerifyForGoodNavigationSection,
  VerifyForGoodResolvedNavigationSection,
} from "../navigation/schema";

type NavigationScenarioKey =
  | "developer"
  | "portal-admin"
  | "customer-admin"
  | "customer-user"
  | "locked-api";

type NavigationScenario = {
  key: NavigationScenarioKey;
  label: string;
  description: string;
  activeNavigationKey:
    | "dashboard"
    | "workspace"
    | "api-access"
    | "usage-billing"
    | "settings";
  plan: PlanCode;
  roles: readonly FrontendAccessRole[];
};

const ADMIN_ROLES: readonly FrontendAccessRole[] = [
  FRONTEND_ACCESS_ROLE.customerAdmin,
  FRONTEND_ACCESS_ROLE.portalAdmin,
];

const BUILDER_ROLES: readonly FrontendAccessRole[] = [
  FRONTEND_ACCESS_ROLE.customerAdmin,
  FRONTEND_ACCESS_ROLE.portalAdmin,
  FRONTEND_ACCESS_ROLE.developer,
];

const ORGANIZATION_MEMBER_ROLES: readonly FrontendAccessRole[] = [
  FRONTEND_ACCESS_ROLE.customerAdmin,
  FRONTEND_ACCESS_ROLE.portalAdmin,
  FRONTEND_ACCESS_ROLE.developer,
];

const navigationFixtureSections: VerifyForGoodNavigationSection[] = [
  {
    key: "review",
    label: "Review",
    helpText: "Verification activity and daily review entry points.",
    items: [
      {
        key: "dashboard",
        label: "Dashboard",
        href: "#/dashboard",
        helpText: "High-level product activity and recent verification signals.",
      },
    ],
  },
  {
    key: "organization",
    label: "Organization",
    helpText: "Tenant context and organization administration surfaces.",
    items: [
      {
        key: "organization-group",
        label: "Organization",
        helpText: "Workspace context and administration views grouped together.",
        children: [
          {
            key: "workspace",
            label: "Overview",
            href: "#/workspace",
            allowedRoles: ORGANIZATION_MEMBER_ROLES,
            helpText:
              "Organization and workspace context for account, tenant, and membership-aware slices.",
          },
          {
            key: "settings",
            label: "Settings",
            href: "#/settings",
            allowedRoles: ADMIN_ROLES,
            helpText: "Organization-level settings and future integrations configuration.",
          },
        ],
      },
    ],
  },
  {
    key: "build",
    label: "Build",
    helpText: "Developer-facing access for API integration and automation.",
    items: [
      {
        key: "integrations-group",
        label: "Integrations",
        helpText: "Automation and API entry points grouped for technical users.",
        children: [
          {
            key: "api-access",
            label: "API",
            href: "#/api-access",
            allowedRoles: BUILDER_ROLES,
            allowedPlans: ["growth", "pro", "enterprise"],
            helpText:
              "Self-serve API credentials and token access. Available on Growth and higher plans.",
            visibility: {
              planRestrictedBehavior: "locked",
            },
          },
        ],
      },
    ],
  },
  {
    key: "account",
    label: "Account",
    helpText: "Commercial and subscription controls for account administrators.",
    items: [
      {
        key: "usage-billing",
        label: "Billing",
        href: "#/usage-billing",
        allowedRoles: ADMIN_ROLES,
        helpText:
          "Subscription, backend-managed billing actions, and usage-aware billing workflows.",
      },
    ],
  },
];

const navigationScenarios: readonly NavigationScenario[] = [
  {
    key: "developer",
    label: "Developer",
    description:
      "Developer view keeps review access plus technical build surfaces without billing controls.",
    activeNavigationKey: "api-access",
    plan: "growth",
    roles: [FRONTEND_ACCESS_ROLE.developer],
  },
  {
    key: "portal-admin",
    label: "Portal Admin",
    description:
      "Portal admin view mirrors admin-oriented customer access until platform-only pages exist.",
    activeNavigationKey: "settings",
    plan: "growth",
    roles: [FRONTEND_ACCESS_ROLE.portalAdmin],
  },
  {
    key: "customer-admin",
    label: "Customer Admin",
    description:
      "Customer admin sees organization settings, API access, and billing alongside daily review.",
    activeNavigationKey: "usage-billing",
    plan: "growth",
    roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
  },
  {
    key: "customer-user",
    label: "Customer User",
    description:
      "Customer user keeps a minimal review-first navigation without administration or build surfaces.",
    activeNavigationKey: "dashboard",
    plan: "growth",
    roles: [FRONTEND_ACCESS_ROLE.customerUser],
  },
  {
    key: "locked-api",
    label: "Locked API",
    description:
      "Free-plan admins still discover API access, but the destination stays visibly locked.",
    activeNavigationKey: "api-access",
    plan: "free",
    roles: [FRONTEND_ACCESS_ROLE.customerAdmin],
  },
];

/**
 * Storybook-style navigation fixture for role-aware, plan-aware, nested, and
 * dark-mode app shell states.
 */
export function NavigationStatesExamples() {
  return (
    <VerifyForGoodMantineProvider>
      <NavigationStatesExamplesInner />
    </VerifyForGoodMantineProvider>
  );
}

function NavigationStatesExamplesInner() {
  const [scenarioKey, setScenarioKey] =
    useState<NavigationScenarioKey>("developer");
  const scenario = useMemo(
    () =>
      navigationScenarios.find((candidate) => candidate.key === scenarioKey) ??
      navigationScenarios[0],
    [scenarioKey],
  );
  const [activeNavigationKey, setActiveNavigationKey] = useState(
    scenario.activeNavigationKey,
  );
  const { resolvedColorScheme, setColorScheme } = useVerifyForGoodColorScheme();

  useEffect(() => {
    setActiveNavigationKey(scenario.activeNavigationKey);
  }, [scenario.activeNavigationKey]);

  const navigationSections = useMemo(
    () =>
      filterNavigationSections(navigationFixtureSections, {
        plan: scenario.plan,
        roles: scenario.roles,
      }),
    [scenario.plan, scenario.roles],
  );

  return (
    <Stack gap="lg">
      <Card
        description="Use these fixtures to inspect role-targeted navigation, locked plan states, nested groups, and dark-mode readability without booting the full portal flow."
        title="Navigation state fixtures"
      >
        <Stack gap="md">
          <Tabs
            onChange={(value) => {
              if (value) {
                setScenarioKey(value as NavigationScenarioKey);
              }
            }}
            value={scenario.key}
          >
            <Tabs.List>
              {navigationScenarios.map((option) => (
                <Tabs.Tab key={option.key} value={option.key}>
                  {option.label}
                </Tabs.Tab>
              ))}
            </Tabs.List>
          </Tabs>

          <Group justify="space-between">
            <Text c="dimmed" fz="sm">
              {scenario.description}
            </Text>
            <Group gap="xs">
              <Button
                onClick={() => setColorScheme("light")}
                size="xs"
                variant={resolvedColorScheme === "light" ? "filled" : "light"}
              >
                Light
              </Button>
              <Button
                onClick={() => setColorScheme("dark")}
                size="xs"
                variant={resolvedColorScheme === "dark" ? "filled" : "light"}
              >
                Dark
              </Button>
            </Group>
          </Group>
        </Stack>
      </Card>

      <VerifyForGoodAppShell
        activeNavigationKey={activeNavigationKey}
        appName="VerifyForGood Navigation Fixture"
        headerActions={
          <Group gap="xs" wrap="nowrap">
            <Text c="dimmed" fz="xs" tt="uppercase">
              {scenario.roles.join(", ")}
            </Text>
            <Text c="dimmed" fz="xs" tt="uppercase">
              Plan: {scenario.plan}
            </Text>
          </Group>
        }
        navigationSections={navigationSections}
        onNavigationChange={(item) =>
          setActiveNavigationKey(item.key as typeof activeNavigationKey)
        }
        sidebarFooter={
          <Card
            description="This fixture intentionally uses nested groups to exercise the shared shell even though the current portal IA remains mostly flat."
            title="Fixture notes"
          >
            <Text c="dimmed" fz="sm">
              Scenario: {scenario.label}
            </Text>
            <Text c="dimmed" fz="sm">
              Visible items: {countVisibleNavigationItems(navigationSections)}
            </Text>
          </Card>
        }
        subtitle="Interactive navigation-only fixture for contributors working on shell behavior."
      >
        <Card
          description="Navigation clicks update the active state locally so contributors can inspect parent highlighting, locked rows, and dark-mode contrast."
          title="Preview guidance"
        >
          <Text c="dimmed" fz="sm">
            Use the scenario tabs to compare developer, admin, and customer-user
            mental models. Use the theme buttons or shell toggle to inspect
            hover, active, focus, and locked states in both light and dark mode.
          </Text>
        </Card>
      </VerifyForGoodAppShell>
    </Stack>
  );
}

function countVisibleNavigationItems(
  sections: readonly VerifyForGoodResolvedNavigationSection[],
) {
  return sections.reduce(
    (total, section) => total + section.items.reduce(countItemTotal, 0),
    0,
  );
}

function countItemTotal(
  total: number,
  item: VerifyForGoodResolvedNavigationSection["items"][number],
): number {
  return total + 1 + (item.children?.reduce(countItemTotal, 0) ?? 0);
}
