import type { VerifyForGoodAppShellSidebarHelpItem } from "@charity-status/shared-ui";
import {
  comparePlansPortalRoute,
  helpDocumentationPortalRoute,
  helpPortalRoute,
  supportContactPortalRoute,
  supportReportIssuePortalRoute,
} from "../app/portalRouteCatalog";

export const portalHelpMenuItems: VerifyForGoodAppShellSidebarHelpItem[] = [
  { key: "help", label: "Help", href: helpPortalRoute.hash },
  { key: "support", label: "Support", href: supportContactPortalRoute.hash },
  {
    key: "documentation",
    label: "Documentation",
    href: helpDocumentationPortalRoute.hash,
  },
  {
    key: "compare-plans",
    label: "Compare Plans",
    href: comparePlansPortalRoute.hash,
  },
  {
    key: "provide-feedback",
    label: "Provide Feedback",
    href: supportReportIssuePortalRoute.hash,
  },
];
