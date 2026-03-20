import { buildApiUrl } from "@charity-status/shared-api";
import { readRuntimeConfig } from "@charity-status/shared-config";
import { AppFrame } from "@charity-status/shared-ui";
import type { FrontendAppInfo } from "@charity-status/shared-types";

const appInfo: FrontendAppInfo = {
  audience: "Authenticated customers managing verification workflows and account settings.",
  description:
    "Foundational shell for future customer portal flows such as billing, usage, and organization settings.",
  title: "Portal workspace shell",
  surface: "portal",
};

const runtimeConfig = readRuntimeConfig(import.meta.env);
const settingsEndpoint = buildApiUrl("/organization/settings", runtimeConfig);

export function App() {
  return (
    <AppFrame app={appInfo} eyebrow="Authenticated Surface">
      <p>
        This placeholder keeps portal wiring isolated from the marketing site while
        leaving room for future auth, billing, and settings slices.
      </p>
      <p>
        Shared backend helpers already normalize the current customer settings endpoint
        as <code>{settingsEndpoint}</code> for <strong>{runtimeConfig.environment}</strong>{" "}
        mode.
      </p>
    </AppFrame>
  );
}
