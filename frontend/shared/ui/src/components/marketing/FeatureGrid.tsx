import { Card, SimpleGrid, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";

export type FeatureGridItem = {
  description: ReactNode;
  eyebrow?: ReactNode;
  title: ReactNode;
};

/**
 * Shared marketing feature grid aligned to the VerifyForGood token system.
 */
export function FeatureGrid({ items }: { items: FeatureGridItem[] }) {
  return (
    <SimpleGrid cols={{ base: 1, md: 2 }} spacing="md">
      {items.map((item) => (
        <Card key={String(item.title)} padding="lg" radius="md" shadow="sm" withBorder>
          <Stack gap="sm">
            {item.eyebrow ? (
              <Text c="dimmed" fw={700} fz="xs" tt="uppercase">
                {item.eyebrow}
              </Text>
            ) : null}
            <Title order={4}>{item.title}</Title>
            <Text c="dimmed" component="div">
              {item.description}
            </Text>
          </Stack>
        </Card>
      ))}
    </SimpleGrid>
  );
}
