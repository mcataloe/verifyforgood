import { AppFrame } from "@charity-status/shared-ui";
import type { FrontendAppInfo } from "@charity-status/shared-types";

const appInfo: FrontendAppInfo = {
  audience: "Public visitors, prospects, and future partner referrals.",
  description:
    "Foundational shell for VerifyForGood marketing experiences, positioning, and conversion paths.",
  title: "Marketing site workspace shell",
  surface: "marketing",
};

export function App() {
  return (
    <AppFrame app={appInfo} eyebrow="Public Surface">
      <p>
        This placeholder keeps public-site concerns separate from the portal while
        exercising the shared frontend foundation packages.
      </p>
    </AppFrame>
  );
}
