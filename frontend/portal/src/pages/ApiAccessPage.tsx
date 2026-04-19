import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import { ApiKeyManager } from "../api-access/ApiKeyManager";
import { PortalPageShell } from "../components/shell";

interface ApiAccessPageProps {
  pane?: CustomerAdminPortalPane | null;
}

export function ApiAccessPage({
  pane: _pane,
}: ApiAccessPageProps) {
  return (
    <PortalPageShell
      description="Create and manage API keys for your organization."
      title="API Access"
    >
      <ApiKeyManager />
    </PortalPageShell>
  );
}
