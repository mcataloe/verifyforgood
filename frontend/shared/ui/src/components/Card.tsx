import {
  Card as MantineCard,
  Group,
  Stack,
  Text,
  type CardProps as MantineCardProps,
} from "@mantine/core";
import type { PropsWithChildren, ReactNode } from "react";

type CardProps = PropsWithChildren<
  Omit<MantineCardProps, "children"> & {
    actions?: ReactNode;
    description?: ReactNode;
    title?: ReactNode;
  }
>;

/**
 * Shared content card wrapper aligned to VerifyForGood spacing and header
 * conventions.
 *
 * Example:
 * ```tsx
 * <Card
 *   title="Verification summary"
 *   description="Recent nonprofit checks and outcome distribution."
 * >
 *   <Text>24 verifications completed in the last 24 hours.</Text>
 * </Card>
 * ```
 */
export function Card({
  actions,
  children,
  description,
  title,
  ...props
}: CardProps) {
  return (
    <MantineCard {...props}>
      {title || description || actions ? (
        <Group align="flex-start" justify="space-between" mb="md" wrap="wrap">
          <Stack gap="xs">
            {title ? <Text fw={600}>{title}</Text> : null}
            {description ? <Text c="dimmed" fz="sm">{description}</Text> : null}
          </Stack>
          {actions ? <Group gap="sm">{actions}</Group> : null}
        </Group>
      ) : null}
      {children}
    </MantineCard>
  );
}
