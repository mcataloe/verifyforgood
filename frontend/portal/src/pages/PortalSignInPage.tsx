import { useId, useState, type FormEvent } from "react";
import {
  Button,
  Divider,
  Group,
  Paper,
  PasswordInput,
  SimpleGrid,
  Stack,
  Text,
  TextInput,
  Title,
} from "@mantine/core";
import type { PortalEndpoints } from "../app/portalEndpoints";
import type { PortalRouteDefinition } from "../app/portalRoutes";
import type { PortalLoginRequest } from "../auth/portalAuthClient";
import {
  PortalActionGroup,
  PortalAnchorButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { usePortalToast } from "../components/feedback";

interface PortalSignInPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onLogin: (request: PortalLoginRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalSignInPage({
  endpoints: _endpoints,
  isBusy,
  onLogin,
  requestedRoute,
}: PortalSignInPageProps) {
  const emailId = useId();
  const passwordId = useId();
  const { dismissToast, showToast } = usePortalToast();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      showToast({
        id: "portal-sign-in",
        message: "Enter both email and password to continue.",
        title: "Sign-in details required",
        tone: "warning",
      });
      return;
    }

    dismissToast("portal-sign-in");

    try {
      await onLogin({
        email,
        password,
      });
    } catch (error) {
      showToast({
        id: "portal-sign-in",
        message: error instanceof Error ? error.message : "Sign-in failed.",
        title: "Unable to sign in",
        tone: "error",
      });
    }
  };

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <Title order={2}>Secure Access for Verification Operations</Title>
          <PortalHint>
            Sign in to continue to {requestedRoute.label}. Use your work email
            and password to access your organization dashboard, billing, team
            access, and verification tools.
          </PortalHint>
        </Stack>

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <AuthInfoCard label="Requested area" value={requestedRoute.label} />
          <AuthInfoCard
            label="Account access"
            value="Secure sign-in for your organization workspace"
          />
          <AuthInfoCard
            label="Need an organization?"
            value="You can create one after signing in if your account is new."
          />
        </SimpleGrid>

        <Paper p="lg" radius="lg" withBorder>
          <Stack gap="sm">
            <Title order={3}>We&apos;ll Take You There</Title>
            <Text component="div" size="sm">
              <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                <li>
                  If you requested a specific area, we&apos;ll return you there after
                  sign-in.
                </li>
                <li>
                  If your account does not belong to an organization yet, you&apos;ll
                  be guided through organization setup next.
                </li>
                <li>
                  Help is available if you need support accessing your account.
                </li>
              </ul>
            </Text>
          </Stack>
        </Paper>
      </Stack>

      <Paper p="lg" radius="xl" withBorder>
        <form noValidate onSubmit={handleSubmit}>
          <Stack gap="lg">
            <Stack gap="xs">
              <Title order={3}>Sign In</Title>
              <PortalHint>Use your work email and password to access the portal.</PortalHint>
            </Stack>

            <TextInput
              autoComplete="email"
              id={emailId}
              label="Email"
              name="email"
              onChange={(event) => {
                dismissToast("portal-sign-in");
                setEmail(event.target.value);
              }}
              placeholder="name@company.com"
              value={email}
            />

            <PasswordInput
              autoComplete="current-password"
              id={passwordId}
              label="Password"
              name="password"
              onChange={(event) => {
                dismissToast("portal-sign-in");
                setPassword(event.target.value);
              }}
              placeholder="Enter your password"
              value={password}
            />

            <PortalActionGroup>
              <Button loading={isBusy} type="submit">
                {isBusy ? "Signing..." : "Sign In"}
              </Button>
              <PortalAnchorButton href="#/register" tone="secondary">
                Create Account
              </PortalAnchorButton>
            </PortalActionGroup>

            <Divider label="Identity providers" labelPosition="center" />

            <Stack gap="sm">
              <Button disabled fullWidth justify="flex-start" type="button" variant="default">
                Google available soon
              </Button>
              <Button disabled fullWidth justify="flex-start" type="button" variant="default">
                Microsoft available soon
              </Button>
            </Stack>

            <Group gap="sm" wrap="wrap">
              <Text component="a" href="#/" size="sm">
                Portal home
              </Text>
              <Text component="a" href="#/register" size="sm">
                Need an account?
              </Text>
              <Text
                component="a"
                href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20password%20help"
                size="sm"
              >
                Forgot password
              </Text>
              <Text
                component="a"
                href="mailto:support@verifyforgood.com?subject=VerifyForGood%20portal%20help"
                size="sm"
              >
                Help
              </Text>
            </Group>
          </Stack>
        </form>
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
