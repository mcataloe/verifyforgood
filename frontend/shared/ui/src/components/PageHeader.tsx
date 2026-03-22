import { Group, Stack, Text, Title, type MantineSpacing } from "@mantine/core";
import type { ReactNode } from "react";

type PageHeaderProps = {
  actions?: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  gap?: MantineSpacing;
  title: ReactNode;
};

/**
 * Shared page-level header for application surfaces.
 *
 * Example:
 * ```tsx
 * <PageHeader
 *   eyebrow="Workspace"
 *   title="Organizations"
 *   description="Monitor account scope, compliance posture, and API usage."
 * />
 * ```
 */
export function PageHeader({
  actions,
  description,
  eyebrow,
  gap = "xs",
  title,
}: PageHeaderProps) {
  return (
    <Group align="flex-start" justify="space-between" wrap="wrap">
      <Stack gap={gap}>
        {eyebrow ? (
          <Text c="dimmed" fw={600} fz="xs" tt="uppercase">
            {eyebrow}
          </Text>
        ) : null}
        <Title order={2}>{title}</Title>
        {description ? (
          <Text c="dimmed" maw="56rem">
            {description}
          </Text>
        ) : null}
      </Stack>
      {actions ? <Group gap="sm">{actions}</Group> : null}
    </Group>
  );
}
