import { Panel } from "@charity-status/shared-ui";
import type { CustomerAdminPortalPane } from "../app/portalNavigation";
import {
  PortalPageShell,
} from "../components/shell";
import { SupportHelpPanel } from "../settings/SupportHelpPanel";
import {
  usePortalSupport,
  type PortalSupportController,
} from "../settings/usePortalSupport";

interface SupportPageProps {
  pane?: CustomerAdminPortalPane | null;
  supportController?: PortalSupportController;
}

export function SupportPage({
  pane,
  supportController,
}: SupportPageProps) {
  const defaultSupportController = usePortalSupport();
  const support = supportController ?? defaultSupportController;
  const supportPane =
    pane === "support-report-issue" ? "report" : "contact";

  return (
    <PortalPageShell
      description="Contact support or report an issue for your organization."
      title="Support"
    >
      <Panel
        subtitle={
          supportPane === "contact"
            ? "Reach the support team and review helpful product links."
            : undefined
        }
        title={supportPane === "contact" ? "Contact Support" : undefined}
      >
        <SupportHelpPanel controller={support} pane={supportPane} />
      </Panel>
    </PortalPageShell>
  );
}
