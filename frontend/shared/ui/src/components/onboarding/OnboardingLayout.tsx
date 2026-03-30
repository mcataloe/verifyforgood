import { SimpleGrid, Stack, Text } from "@mantine/core";
import type { ReactNode } from "react";
import { PageHeader } from "../PageHeader";
import {
  ProgressIndicator,
  type OnboardingProgressStep,
} from "./ProgressIndicator";
import { StepCard } from "./StepCard";

export type OnboardingStep = OnboardingProgressStep & {
  action?: ReactNode;
  description: ReactNode;
};

/**
 * Shared onboarding scaffold for welcome and first-run customer flows.
 */
export function OnboardingLayout({
  eyebrow = "Onboarding",
  steps,
  subtitle,
  title,
}: {
  eyebrow?: ReactNode;
  steps: OnboardingStep[];
  subtitle?: ReactNode;
  title: ReactNode;
}) {
  return (
    <Stack gap="lg">
      <PageHeader description={subtitle} eyebrow={eyebrow} title={title} />

      <ProgressIndicator
        steps={steps.map(({ key, label, status }) => ({ key, label, status }))}
      />

      <SimpleGrid cols={{ base: 1, lg: 2 }} spacing="md">
        {steps.map((step, index) => (
          <StepCard
            action={step.action}
            description={step.description}
            index={index + 1}
            key={step.key}
            status={step.status}
            title={step.label}
          />
        ))}
      </SimpleGrid>

      <Text c="dimmed" fz="sm">
        Placeholder onboarding content should stay business-logic free until the
        product sequence is finalized.
      </Text>
    </Stack>
  );
}
