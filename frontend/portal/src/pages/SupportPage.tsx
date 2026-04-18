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
      eyebrow="Support"
      title="Support & Help"
    >
      <Panel
        subtitle={
          supportPane === "contact"
            ? "Reach the support team and review helpful product links."
            : "Send an issue report or recommendation to the support team."
        }
        title={
          supportPane === "contact" ? "Contact Support" : "Report An Issue"
        }
      >
        <SupportHelpPanel controller={support} pane={supportPane} />
      </Panel>
    </PortalPageShell>
  );
}
