import { ApiKeyManager } from "../api-access/ApiKeyManager";
import { PortalPageShell } from "../components/shell";

export function ApiAccessPage() {
  return (
    <PortalPageShell
      description="Create and manage API keys for your organization."
      title="API Access"
    >
      <ApiKeyManager />
    </PortalPageShell>
  );
}
