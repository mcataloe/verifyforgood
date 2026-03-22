import { Button, Stack } from "@mantine/core";
import { EmptyState } from "./EmptyState";
import { ErrorState } from "./ErrorState";
import { LoadingSkeleton } from "./LoadingSkeleton";

/**
 * Storybook-style examples for shared loading, empty, and error state
 * patterns.
 */
export function FeedbackStatesExamples() {
  return (
    <Stack gap="lg">
      <LoadingSkeleton
        description="Preparing the latest verification activity for this workspace."
        title="Loading verification activity"
        variant="table"
      />

      <EmptyState
        action={<Button variant="light">Add organization</Button>}
        preset="organizations"
      />

      <EmptyState
        action={<Button variant="light">Run verification</Button>}
        preset="verifications"
      />

      <EmptyState
        action={<Button variant="light">Create API key</Button>}
        preset="api-keys"
      />

      <ErrorState
        action={<Button variant="light">Retry request</Button>}
        description="The latest verification records could not be loaded from the API."
      />
    </Stack>
  );
}
