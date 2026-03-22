import { Box, Group, Stack, Text } from "@mantine/core";
import { useVerifyForGoodSemanticColors } from "../../theme/useVerifyForGoodTheme";
import { verifyForGoodTokens } from "../../theme/tokens";

export type OnboardingStepStatus = "complete" | "current" | "upcoming";

export type OnboardingProgressStep = {
  key: string;
  label: string;
  status: OnboardingStepStatus;
};

/**
 * Compact progress indicator for low-friction onboarding flows.
 */
export function ProgressIndicator({
  steps,
}: {
  steps: OnboardingProgressStep[];
}) {
  const { palette, semantic } = useVerifyForGoodSemanticColors();

  return (
    <Stack gap="sm">
      <Group
        aria-label="Onboarding progress"
        component="ol"
        gap="sm"
        role="list"
        wrap="wrap"
      >
        {steps.map((step, index) => {
          const isComplete = step.status === "complete";
          const isCurrent = step.status === "current";

          return (
            <Group
              component="li"
              gap="sm"
              key={step.key}
              role="listitem"
              wrap="nowrap"
            >
              <Group gap="xs" wrap="nowrap">
                <Box
                  aria-hidden="true"
                  style={{
                    alignItems: "center",
                    backgroundColor:
                      isComplete || isCurrent
                        ? palette.primary[500]
                        : semantic.surface_subtle,
                    border: `1px solid ${
                      isComplete || isCurrent
                        ? palette.primary[500]
                        : semantic.border
                    }`,
                    borderRadius: "999px",
                    color:
                      isComplete || isCurrent
                        ? palette.neutral[0]
                        : semantic.text_secondary,
                    display: "inline-flex",
                    fontSize: verifyForGoodTokens.typography.fontSize.xs,
                    fontWeight: verifyForGoodTokens.typography.fontWeight.bold,
                    height: `${verifyForGoodTokens.spacing.baseUnit * 3}px`,
                    justifyContent: "center",
                    width: `${verifyForGoodTokens.spacing.baseUnit * 3}px`,
                  }}
                >
                  {index + 1}
                </Box>
                <Text fw={isCurrent ? 700 : 500}>{step.label}</Text>
              </Group>
              {index < steps.length - 1 ? (
                <Box
                  aria-hidden="true"
                  style={{
                    backgroundColor: isComplete
                      ? palette.primary[400]
                      : semantic.border,
                    borderRadius: "999px",
                    height: "1px",
                    minWidth: `${verifyForGoodTokens.spacing.baseUnit * 5}px`,
                  }}
                />
              ) : null}
            </Group>
          );
        })}
      </Group>
    </Stack>
  );
}
