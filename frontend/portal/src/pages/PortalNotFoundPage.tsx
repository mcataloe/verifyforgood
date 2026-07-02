import { EmptyState } from "@charity-status/shared-ui";
import { organizationsPortalRoute } from "../app/portalRoutes";
import { PortalPageShell } from "../components/shell";

export function PortalNotFoundPage() {
  return (
    <PortalPageShell
      description="The requested portal destination does not exist or is no longer available."
      eyebrow="Navigation"
      title="Page not found"
    >
      <EmptyState
        action={
          <a className="portal-shell__action" href={organizationsPortalRoute.hash}>
            Open organizations
          </a>
        }
        description="Use the portal navigation or return to organization search."
        title="This route is unavailable"
      />
    </PortalPageShell>
  );
}
