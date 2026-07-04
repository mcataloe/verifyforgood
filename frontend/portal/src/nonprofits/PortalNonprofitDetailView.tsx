import {
  DetailFieldList,
  DetailStack,
  EntityDetailLayout,
  StatusBadge,
} from "@charity-status/shared-ui";
import type { OrganizationDetailSection } from "../app/portalRoutes";
import { usePortalToast } from "../components/feedback";
import { PortalButton } from "../components/PortalPrimitives";
import type { PortalNonprofitDetail } from "./nonprofitSearch";
import {
  buildComplianceItems,
  buildFilingsItems,
  buildOverviewItems,
  buildSummaryItems,
  PortalNonprofitSourceSection,
} from "./portalNonprofitDetailFields";
import { detailStatus, summaryStatus } from "./portalNonprofitStatus";

interface PortalNonprofitDetailViewProps {
  activeSection?: OrganizationDetailSection;
  detail: PortalNonprofitDetail;
  onBackToSearch?: () => void;
  onSectionChange?: (section: OrganizationDetailSection) => void;
}

export function PortalNonprofitDetailView({
  activeSection,
  detail,
  onBackToSearch,
  onSectionChange,
}: PortalNonprofitDetailViewProps) {
  const { showToast } = usePortalToast();

  return (
    <EntityDetailLayout
      actions={
        onBackToSearch ? (
          <PortalButton
            onClick={onBackToSearch}
            tone="secondary"
            type="button"
          >
            Back to search
          </PortalButton>
        ) : null
      }
      activeTabKey={activeSection}
      description="Shared organization detail layout for trust-forward entity review."
      ein={detail.ein}
      name={detail.name}
      onPrimaryAction={() => {
        showToast({
          message:
            "Queuing an entity review isn't wired up yet — this is coming soon.",
          title: "Not available yet",
          tone: "warning",
        });
      }}
      onTabChange={(key) => onSectionChange?.(key as OrganizationDetailSection)}
      primaryActionLabel="Queue review"
      status={detailStatus(detail)}
      summaryItems={buildSummaryItems(detail)}
      tabs={[
        {
          key: "overview",
          label: "Overview",
          content: <DetailFieldList items={buildOverviewItems(detail)} />,
        },
        {
          key: "filings",
          label: "Filings",
          content: <DetailFieldList items={buildFilingsItems(detail)} />,
        },
        {
          key: "compliance",
          label: "Compliance",
          content: <DetailFieldList items={buildComplianceItems(detail)} />,
        },
        {
          key: "sources",
          label: "Sources",
          content: <PortalNonprofitSourceSection detail={detail} />,
        },
        {
          key: "activity",
          label: "Activity Log",
          content: <ActivityPlaceholder />,
        },
      ]}
    />
  );
}

export function PortalNonprofitEmbeddedDetail({
  detail,
}: PortalNonprofitDetailViewProps) {
  return (
    <article className="portal-nonprofit-embedded-detail">
      <header className="portal-nonprofit-embedded-detail__header">
        <div className="portal-nonprofit-embedded-detail__title-row">
          <h3>{detail.name}</h3>
          <StatusBadge status={detailStatus(detail)} />
        </div>
        <p className="portal-nonprofit-embedded-detail__identifier">
          EIN {detail.ein}
        </p>
        <DetailFieldList items={buildSummaryItems(detail)} />
      </header>
      <div className="portal-nonprofit-embedded-detail__sections">
        <DetailStack title="Overview">
          <DetailFieldList items={buildOverviewItems(detail)} />
        </DetailStack>
        <DetailStack title="Filings">
          <DetailFieldList items={buildFilingsItems(detail)} />
        </DetailStack>
        <DetailStack title="Compliance">
          <DetailFieldList items={buildComplianceItems(detail)} />
        </DetailStack>
        <DetailStack title="Sources">
          <PortalNonprofitSourceSection detail={detail} />
        </DetailStack>
        <DetailStack title="Activity">
          <ActivityPlaceholder />
        </DetailStack>
      </div>
    </article>
  );
}

function ActivityPlaceholder() {
  return (
    <ul className="portal-list">
      <li>Initial lookup completed for this entity.</li>
      <li>Recent filing metadata has been attached to the review record.</li>
      <li>
        Detailed activity history can replace this placeholder once the event
        feed exists.
      </li>
    </ul>
  );
}

export { detailStatus, summaryStatus };
