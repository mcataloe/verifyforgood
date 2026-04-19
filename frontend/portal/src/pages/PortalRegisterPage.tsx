import { useId, useState, type FormEvent } from "react";
import {
  Button,
  Divider,
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
import type { PortalRegisterRequest } from "../auth/portalAuthClient";
import {
  PortalActionGroup,
  PortalAnchorButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { usePortalToast } from "../components/feedback";

interface PortalRegisterPageProps {
  endpoints: PortalEndpoints;
  isBusy: boolean;
  onRegister: (request: PortalRegisterRequest) => Promise<unknown>;
  requestedRoute: PortalRouteDefinition;
}

export function PortalRegisterPage({
  endpoints: _endpoints,
  isBusy,
  onRegister,
  requestedRoute,
}: PortalRegisterPageProps) {
  const fullNameId = useId();
  const emailId = useId();
  const passwordId = useId();
  const { dismissToast, showToast } = usePortalToast();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    if (!email.trim() || !password.trim()) {
      showToast({
        id: "portal-register",
        message: "Enter an email and password to create your account.",
        title: "Account details required",
        tone: "warning",
      });
      return;
    }

    dismissToast("portal-register");

    try {
      await onRegister({
        email,
        full_name: fullName.trim() || undefined,
        password,
      });
    } catch (error) {
      showToast({
        id: "portal-register",
        message: error instanceof Error ? error.message : "Registration failed.",
        title: "Unable to create account",
        tone: "error",
      });
    }
  };

  return (
    <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="xl">
      <Stack gap="lg">
        <Stack gap="xs">
          <Title order={2}>Start Your Portal Account</Title>
          <PortalHint>
            Create an account to continue to {requestedRoute.label}. Once your
            account is ready, you can sign in and finish setting up your
            organization if needed.
          </PortalHint>
        </Stack>

        <SimpleGrid cols={{ base: 1, sm: 3 }} spacing="sm">
          <AuthInfoCard label="Requested area" value={requestedRoute.label} />
          <AuthInfoCard
            label="Account setup"
            value="Create your login for the customer portal"
          />
          <AuthInfoCard
            label="Next step"
            value="After sign-up, you can create or join an organization."
          />
        </SimpleGrid>

        <Paper p="lg" radius="lg" withBorder>
          <Stack gap="sm">
            <Title order={3}>Create Your Account First</Title>
            <Text component="div" size="sm">
              <ul style={{ margin: 0, paddingLeft: "1.2rem" }}>
                <li>Create your account with your work details.</li>
                <li>
                  After sign-in, we&apos;ll check whether you already belong to an
                  organization.
                </li>
                <li>
                  If you do not, you can create one in a dedicated setup step.
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
              <Title order={3}>Create Account</Title>
              <PortalHint>Use your work email to create your portal login.</PortalHint>
            </Stack>

            <TextInput
              autoComplete="name"
              id={fullNameId}
              label="Full name"
              name="full_name"
              onChange={(event) => {
                dismissToast("portal-register");
                setFullName(event.target.value);
              }}
              placeholder="Alex Operator"
              value={fullName}
            />

            <TextInput
              autoComplete="email"
              id={emailId}
              label="Email"
              name="email"
              onChange={(event) => {
                dismissToast("portal-register");
                setEmail(event.target.value);
              }}
              placeholder="name@company.com"
              type="email"
              value={email}
            />

            <PasswordInput
              autoComplete="new-password"
              id={passwordId}
              label="Password"
              name="password"
              onChange={(event) => {
                dismissToast("portal-register");
                setPassword(event.target.value);
              }}
              placeholder="Choose a password"
              value={password}
            />

            <PortalActionGroup>
              <Button loading={isBusy} type="submit">
                {isBusy ? "Creating..." : "Create Account"}
              </Button>
              <PortalAnchorButton href="#/sign-in" tone="secondary">
                Back
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
