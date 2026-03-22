import { Box, Stack, Text, Title } from "@mantine/core";
import { useComputedColorScheme } from "@mantine/core";
import type { ReactNode } from "react";
import { verifyForGoodTokens } from "../theme/tokens";

export type EmptyStatePreset = "api-keys" | "organizations" | "verifications";

type EmptyStateProps = {
  action?: ReactNode;
  description?: ReactNode;
  preset?: EmptyStatePreset;
  title?: ReactNode;
};

const EMPTY_STATE_PRESETS: Record<
  EmptyStatePreset,
  { description: string; title: string }
> = {
  organizations: {
    title: "No organizations yet",
    description:
      "Add your first organization to establish workspace scope and start verification workflows.",
  },
  verifications: {
    title: "No verifications yet",
    description:
      "Run a verification to build your audit trail and monitor nonprofit status changes over time.",
  },
  "api-keys": {
    title: "No API keys created",
    description:
      "Create an API key when you are ready to connect your internal systems to VerifyForGood.",
  },
};

/**
 * Reusable no-data state with calm enterprise copy and preset examples for
 * common product surfaces.
 *
 * Example:
 * ```tsx
 * <EmptyState
 *   preset="verifications"
 *   action={<Button>Create verification</Button>}
 * />
 * ```
 */
export function EmptyState({
  action,
  description,
  preset,
  title,
}: EmptyStateProps) {
  const resolvedColorScheme = useComputedColorScheme("light");
  const semantic =
    verifyForGoodTokens.color.semantic[
      resolvedColorScheme === "dark" ? "dark" : "light"
    ];
  const presetContent = preset ? EMPTY_STATE_PRESETS[preset] : null;

  return (
    <Box
      style={{
        backgroundColor: semantic.surface,
        border: `1px solid ${semantic.border}`,
        borderRadius: verifyForGoodTokens.radius.card,
        boxShadow: verifyForGoodTokens.shadow.subtle,
        padding: verifyForGoodTokens.spacing.scale.xl,
      }}
    >
      <Stack align="center" gap="md" ta="center">
        <EmptyStateGlyph />
        <Stack gap="xs" maw="32rem">
          <Text c="dimmed" fw={600} fz="xs" tt="uppercase">
            Empty state
          </Text>
          <Title order={3}>{title ?? presetContent?.title ?? "Nothing to show yet"}</Title>
          <Text c="dimmed" component="div">
            {description ??
              presetContent?.description ??
              "Content will appear here once records are available."}
          </Text>
        </Stack>
        {action ? <Box>{action}</Box> : null}
      </Stack>
    </Box>
  );
}

function EmptyStateGlyph() {
  const resolvedColorScheme = useComputedColorScheme("light");
  const semantic =
    verifyForGoodTokens.color.semantic[
      resolvedColorScheme === "dark" ? "dark" : "light"
    ];

  return (
    <Box
      aria-hidden="true"
      style={{
        alignItems: "center",
        backgroundColor: semantic.surface_subtle,
        border: `1px solid ${semantic.border}`,
        borderRadius: verifyForGoodTokens.radius.modal,
        display: "grid",
        gap: verifyForGoodTokens.spacing.baseUnit / 2,
        justifyItems: "center",
        padding: verifyForGoodTokens.spacing.scale.md,
      }}
    >
      <Box
        style={{
          backgroundColor: verifyForGoodTokens.color.palette.primary[200],
          borderRadius: verifyForGoodTokens.radius.button,
          height: `${verifyForGoodTokens.spacing.baseUnit * 1.5}px`,
          width: `${verifyForGoodTokens.spacing.baseUnit * 8}px`,
        }}
      />
      <Box
        style={{
          backgroundColor: verifyForGoodTokens.color.palette.neutral[300],
          borderRadius: verifyForGoodTokens.radius.button,
          height: `${verifyForGoodTokens.spacing.baseUnit * 1.5}px`,
          width: `${verifyForGoodTokens.spacing.baseUnit * 12}px`,
        }}
      />
      <Box
        style={{
          backgroundColor: verifyForGoodTokens.color.palette.neutral[200],
          borderRadius: verifyForGoodTokens.radius.button,
          height: `${verifyForGoodTokens.spacing.baseUnit * 1.5}px`,
          width: `${verifyForGoodTokens.spacing.baseUnit * 10}px`,
        }}
      />
    </Box>
  );
}
