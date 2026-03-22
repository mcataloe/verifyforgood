import { Card, Group, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

/**
 * Shared marketing CTA block with a calm, low-pressure presentation.
 */
export function CallToAction({
  actions,
  description,
  title,
}: {
  actions?: ReactNode;
  description: ReactNode;
  title: ReactNode;
}) {
  return (
    <Card padding="xl" radius="lg" shadow="sm" withBorder>
      <Stack gap="md">
        <Stack gap="xs">
          <Title order={3}>{title}</Title>
          <Text c="dimmed" component="div">
            {description}
          </Text>
        </Stack>
        {actions ? <Group gap="sm">{actions}</Group> : null}
      </Stack>
    </Card>
  );
}
