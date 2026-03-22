import { Badge, Box, Button, Group, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import { useVerifyForGoodSemanticColors } from "../../theme/useVerifyForGoodTheme";
import { verifyForGoodTokens } from "../../theme/tokens";
import type { OnboardingStepStatus } from "./ProgressIndicator";

type StepCardProps = {
  action?: ReactNode;
  description: ReactNode;
  index: number;
  status: OnboardingStepStatus;
  title: ReactNode;
};

/**
 * Reusable onboarding checklist card.
 */
export function StepCard({
  action,
  description,
  index,
  status,
  title,
}: StepCardProps) {
  const { palette, semantic } = useVerifyForGoodSemanticColors();
  const accent =
    status === "complete"
      ? palette.success[500]
      : status === "current"
        ? palette.primary[500]
        : semantic.border;

  return (
    <Box
      style={{
        backgroundColor: semantic.surface,
        border: `1px solid ${semantic.border}`,
        borderLeft: `${verifyForGoodTokens.spacing.baseUnit / 2}px solid ${accent}`,
        borderRadius: verifyForGoodTokens.radius.card,
        padding: verifyForGoodTokens.spacing.scale.lg,
      }}
    >
      <Stack gap="sm">
        <Group justify="space-between" wrap="wrap">
          <Group gap="sm" wrap="nowrap">
            <Badge color={status === "complete" ? "success" : "primary"} variant="light">
              Step {index}
            </Badge>
            <Title order={4}>{title}</Title>
          </Group>
          <Badge color={statusBadgeColor(status)} variant="light">
            {statusBadgeLabel(status)}
          </Badge>
        </Group>
        <Text c="dimmed" component="div">
          {description}
        </Text>
        {action ?? <Button variant="light">Continue</Button>}
      </Stack>
    </Box>
  );
}

function statusBadgeColor(status: OnboardingStepStatus) {
  switch (status) {
    case "complete":
      return "success";
    case "current":
      return "primary";
    default:
      return "gray";
  }
}

function statusBadgeLabel(status: OnboardingStepStatus) {
  switch (status) {
    case "complete":
      return "Complete";
    case "current":
      return "Current";
    default:
      return "Upcoming";
  }
}
