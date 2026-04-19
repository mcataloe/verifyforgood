import {
  Container,
  Page,
  Panel,
  Section,
} from "@charity-status/shared-ui";
import { Stack, Text, Title } from "@mantine/core";
import type {
  FrontendAppInfo,
  FrontendRuntimeConfig,
} from "@charity-status/shared-types";
import type { PropsWithChildren } from "react";

interface PortalAuthLayoutProps extends PropsWithChildren {
  app: FrontendAppInfo;
  containerSize?: "content" | "full" | "narrow" | "wide";
  runtimeConfig: FrontendRuntimeConfig;
  subtitle: string;
  title: string;
}

export function PortalAuthLayout({
  app,
  children,
  containerSize = "narrow",
  runtimeConfig,
  subtitle,
  title,
}: PortalAuthLayoutProps) {
  return (
    <Page>
      <Section>
        <Container size={containerSize}>
          <Stack gap="xl" py="xl">
            <Stack gap="sm">
              <Title order={1}>{title}</Title>
              <Text c="dimmed" maw={720}>
                {subtitle}
              </Text>
            </Stack>

            <Panel
              title={app.title}
              subtitle="Sign in to manage your organization, billing, team access, and verification activity."
            >
              {children}
            </Panel>
          </Stack>
        </Container>
      </Section>
    </Page>
  );
}
