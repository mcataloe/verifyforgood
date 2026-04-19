import { Divider, List, Paper, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import {
  PortalActionGroup,
  PortalAnchorButton,
  PortalHint,
} from "../components/PortalPrimitives";
import type { PortalRouteDefinition } from "../app/portalRoutes";

interface PortalHomePageProps {
  requestedRoute: PortalRouteDefinition;
}

export function PortalHomePage({ requestedRoute }: PortalHomePageProps) {
  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <Title order={2}>Sign In to Manage Your Organization</Title>
          <PortalHint>
            Access billing, team access, API credentials, and verification
            activity from one secure account. Sign in first, then create or
            join an organization if needed.
          </PortalHint>
        </Stack>

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <AuthInfoCard
            label="Primary next step"
            value="Sign in or create an account"
          />
          <AuthInfoCard
            label="After authentication"
            value={
              requestedRoute.key === "home"
                ? "You will continue to your dashboard or organization setup."
                : `You will continue to ${requestedRoute.label}.`
            }
          />
          <AuthInfoCard
            label="Organization setup"
            value="Organization setup appears only if your account does not already belong to an organization."
          />
        </SimpleGrid>

        <Paper p="lg" radius="lg" withBorder>
          <Stack gap="sm">
            <Title order={3}>Get Started Quickly</Title>
            <List spacing="xs">
              <List.Item>
                If you already belong to an organization, you go straight to your
                dashboard.
              </List.Item>
              <List.Item>
                If you are new, you can create your organization in a dedicated
                setup step.
              </List.Item>
              <List.Item>
                Your account is always authenticated before organization setup.
              </List.Item>
            </List>
          </Stack>
        </Paper>
      </Stack>

      <Paper p="lg" radius="xl" withBorder>
        <Stack gap="lg">
          <Stack gap="xs">
            <Title order={3}>Start with Authentication</Title>
            <PortalHint>Choose the account flow that fits your current state.</PortalHint>
          </Stack>

          <PortalActionGroup>
            <div data-testid="public-home-auth-cta">
              <PortalActionGroup>
                <PortalAnchorButton href="#/sign-in" tone="primary">
                  Sign In
                </PortalAnchorButton>
                <PortalAnchorButton href="#/register" tone="secondary">
                  Create Account
                </PortalAnchorButton>
              </PortalActionGroup>
            </div>
          </PortalActionGroup>

          <Divider label="What you can manage" labelPosition="center" />

          <List spacing="xs">
            <List.Item>Verification dashboard and organization activity</List.Item>
            <List.Item>Nonprofit search and detailed review</List.Item>
            <List.Item>Usage, billing, settings, and API credential management</List.Item>
          </List>
        </Stack>
      </Paper>
    </SimpleGrid>
  );
}

function AuthInfoCard({ label, value }: { label: string; value: string }) {
  return (
    <Paper p="md" radius="md" withBorder>
      <Stack gap={4}>
        <Text c="dimmed" fw={700} fz="xs" tt="uppercase">
          {label}
        </Text>
        <Text size="sm">{value}</Text>
      </Stack>
    </Paper>
  );
}
