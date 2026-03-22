import { Button } from "@mantine/core";
import { OnboardingLayout } from "./onboarding/OnboardingLayout";

/**
 * Storybook-style example for the shared onboarding flow primitives.
 */
export function OnboardingFlowExamples() {
  return (
    <OnboardingLayout
      steps={[
        {
          key: "welcome",
          label: "Welcome",
          status: "complete",
          description:
            "Review workspace scope, plan boundaries, and the first steps for a calm rollout.",
          action: <Button variant="subtle">Review workspace</Button>,
        },
        {
          key: "verification",
          label: "Create first verification",
          status: "current",
          description:
            "Run the first verification request to see the organization review workflow in context.",
        },
        {
          key: "api-key",
          label: "Generate API key",
          status: "upcoming",
          description:
            "Create an integration key only when your team is ready to connect internal systems.",
        },
        {
          key: "invite",
          label: "Invite team member",
          status: "upcoming",
          description:
            "Add a teammate once ownership, review cadence, and data access are clear.",
        },
      ]}
      subtitle="A low-friction setup flow for new VerifyForGood customers."
      title="Get started with confidence"
    />
  );
}
