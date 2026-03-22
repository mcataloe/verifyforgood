import { Box, Stack, Text, Title } from "@mantine/core";
import { useComputedColorScheme } from "@mantine/core";
import type { ReactNode } from "react";
import { verifyForGoodTokens } from "../theme/tokens";

type ErrorStateProps = {
  action?: ReactNode;
  description?: ReactNode;
  title?: ReactNode;
};

/**
 * Shared error state for recoverable failures such as loading or submission
 * errors.
 *
 * Example:
 * ```tsx
 * <ErrorState
 *   description="The latest verification records could not be loaded."
 *   action={<Button variant=\"light\">Retry</Button>}
 * />
 * ```
 */
export function ErrorState({
  action,
  description = "We could not load this content right now. Please try again in a moment.",
  title = "Something went wrong",
}: ErrorStateProps) {
  const resolvedColorScheme = useComputedColorScheme("light");
  const semantic =
    verifyForGoodTokens.color.semantic[
      resolvedColorScheme === "dark" ? "dark" : "light"
    ];
  const accent =
    resolvedColorScheme === "dark"
      ? verifyForGoodTokens.color.palette.danger[400]
      : verifyForGoodTokens.color.palette.danger[500];
  const accentBackground =
    resolvedColorScheme === "dark"
      ? verifyForGoodTokens.color.palette.danger[950]
      : verifyForGoodTokens.color.palette.danger[50];

  return (
    <Box
      role="alert"
      style={{
        backgroundColor: semantic.surface,
        border: `1px solid ${semantic.border}`,
        borderLeft: `${verifyForGoodTokens.spacing.baseUnit / 2}px solid ${accent}`,
        borderRadius: verifyForGoodTokens.radius.card,
        boxShadow: verifyForGoodTokens.shadow.subtle,
        padding: verifyForGoodTokens.spacing.scale.lg,
      }}
    >
      <Stack gap="md">
        <Box
          aria-hidden="true"
          style={{
            backgroundColor: accentBackground,
            borderRadius: verifyForGoodTokens.radius.button,
            color: accent,
            display: "inline-flex",
            fontFamily: verifyForGoodTokens.typography.fontFamily.mono,
            fontSize: verifyForGoodTokens.typography.fontSize.sm,
            fontWeight: verifyForGoodTokens.typography.fontWeight.bold,
            letterSpacing: verifyForGoodTokens.typography.letterSpacing.caps,
            padding: `${verifyForGoodTokens.spacing.baseUnit / 2}px ${verifyForGoodTokens.spacing.baseUnit}px`,
            width: "fit-content",
          }}
        >
          ERROR
        </Box>
        <Stack gap="xs">
          <Title order={3}>{title}</Title>
          <Text c="dimmed" component="div">
            {description}
          </Text>
        </Stack>
        {action ? <Box>{action}</Box> : null}
      </Stack>
    </Box>
  );
}
