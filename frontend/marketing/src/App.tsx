import { buildApiUrl } from "@charity-status/shared-api";
import { readRuntimeConfig } from "@charity-status/shared-config";
import { AppFrame } from "@charity-status/shared-ui";
import type { FrontendAppInfo } from "@charity-status/shared-types";

const appInfo: FrontendAppInfo = {
  audience: "Public visitors, prospects, and future partner referrals.",
  description:
    "Foundational shell for VerifyForGood marketing experiences, positioning, and conversion paths.",
  title: "Marketing site workspace shell",
  surface: "marketing",
};

const runtimeConfig = readRuntimeConfig(import.meta.env);
const publicSearchEndpoint = buildApiUrl("/nonprofits/search", runtimeConfig);

export function App() {
  return (
    <AppFrame app={appInfo} eyebrow="Public Surface">
      <p>
        This placeholder keeps public-site concerns separate from the portal while
        exercising the shared frontend foundation packages.
      </p>
      <p>
        Shared runtime config currently resolves the public API target as{" "}
        <code>{publicSearchEndpoint}</code> for <strong>{runtimeConfig.environment}</strong>{" "}
        mode.
      </p>
    </AppFrame>
  );
}
