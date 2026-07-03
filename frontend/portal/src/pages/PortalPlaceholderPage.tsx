import { EmptyState } from "@charity-status/shared-ui";
import { PortalPageShell } from "../components/shell";

interface PortalPlaceholderPageProps {
  description: string;
  title: string;
}

export function PortalPlaceholderPage({
  description,
  title,
}: PortalPlaceholderPageProps) {
  return (
    <PortalPageShell description={description} title={title}>
      <EmptyState
        description="This section will need to be built out."
        title="Coming soon"
      />
    </PortalPageShell>
  );
}
