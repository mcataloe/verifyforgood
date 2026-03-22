import {
  Box,
  Group,
  Skeleton,
  Stack,
  Text,
  VisuallyHidden,
} from "@mantine/core";
import { useComputedColorScheme } from "@mantine/core";
import type { ReactNode } from "react";
import { verifyForGoodTokens } from "../theme/tokens";

export type LoadingSkeletonVariant = "card" | "table";

type LoadingSkeletonProps = {
  description?: ReactNode;
  rows?: number;
  title?: ReactNode;
  variant?: LoadingSkeletonVariant;
};

/**
 * Loading placeholder for dashboard cards, tables, and lightweight content
 * panels.
 *
 * Example:
 * ```tsx
 * <LoadingSkeleton
 *   title="Loading organizations"
 *   description="Preparing organization records for this workspace."
 *   variant="table"
 *   rows={4}
 * />
 * ```
 */
export function LoadingSkeleton({
  description = "Fetching the latest workspace data.",
  rows = 4,
  title = "Loading content",
  variant = "card",
}: LoadingSkeletonProps) {
  const resolvedColorScheme = useComputedColorScheme("light");
  const semantic =
    verifyForGoodTokens.color.semantic[
      resolvedColorScheme === "dark" ? "dark" : "light"
    ];

  return (
    <Box
      aria-busy="true"
      aria-live="polite"
      role="status"
      style={{
        backgroundColor: semantic.surface,
        border: `1px solid ${semantic.border}`,
        borderRadius: verifyForGoodTokens.radius.card,
        boxShadow: verifyForGoodTokens.shadow.subtle,
        padding: verifyForGoodTokens.spacing.scale.lg,
      }}
    >
      <VisuallyHidden>{title}</VisuallyHidden>
      <Stack gap="md">
        <Stack gap="xs">
          <Text c="dimmed" fw={600} fz="xs" tt="uppercase">
            Loading
          </Text>
          <Text fw={600}>{title}</Text>
          <Text c="dimmed" component="div" fz="sm">
            {description}
          </Text>
        </Stack>

        {variant === "table" ? <TableSkeleton rows={rows} /> : <CardSkeleton />}
      </Stack>
    </Box>
  );
}

function CardSkeleton() {
  return (
    <Stack gap="sm">
      <Skeleton height={16} radius="xl" width="42%" />
      <Skeleton height={44} radius="md" width="68%" />
      <Skeleton height={12} radius="xl" width="100%" />
      <Skeleton height={12} radius="xl" width="78%" />
      <Group grow>
        <Skeleton height={72} radius="md" />
        <Skeleton height={72} radius="md" />
      </Group>
    </Stack>
  );
}

function TableSkeleton({ rows }: { rows: number }) {
  return (
    <Stack gap="sm">
      <Group grow wrap="nowrap">
        <Skeleton height={14} radius="xl" width="34%" />
        <Skeleton height={14} radius="xl" width="22%" />
        <Skeleton height={14} radius="xl" width="20%" />
      </Group>
      {Array.from({ length: rows }, (_, index) => (
        <Group key={index} grow wrap="nowrap">
          <Skeleton height={36} radius="md" width="44%" />
          <Skeleton height={36} radius="md" width="28%" />
          <Skeleton height={36} radius="md" width="18%" />
        </Group>
      ))}
    </Stack>
  );
}
