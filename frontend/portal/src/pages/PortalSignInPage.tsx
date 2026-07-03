import { useId, useState, type FormEvent } from "react";
import {
  Button,
  Divider,
  Group,
  Paper,
  PasswordInput,
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
  isBusy,
  onLogin,
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
    <Paper maw={440} mx="auto" p="lg" radius="xl" w="100%" withBorder>
      <form noValidate onSubmit={handleSubmit}>
        <Stack gap="lg">
          <Stack gap="xs">
            <Title order={3}>Sign In</Title>
            <PortalHint>
              Use your work email and password to access the portal.
            </PortalHint>
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
            <Button
              disabled
              fullWidth
              justify="flex-start"
              type="button"
              variant="default"
            >
              Google available soon
            </Button>
            <Button
              disabled
              fullWidth
              justify="flex-start"
              type="button"
              variant="default"
            >
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
  );
}
