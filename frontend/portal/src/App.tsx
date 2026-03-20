import { AppFrame } from "@charity-status/shared-ui";
import type { FrontendAppInfo } from "@charity-status/shared-types";

const appInfo: FrontendAppInfo = {
  audience: "Authenticated customers managing verification workflows and account settings.",
  description:
    "Foundational shell for future customer portal flows such as billing, usage, and organization settings.",
  title: "Portal workspace shell",
  surface: "portal",
};

export function App() {
  return (
    <AppFrame app={appInfo} eyebrow="Authenticated Surface">
      <p>
        This placeholder keeps portal wiring isolated from the marketing site while
        leaving room for future auth, billing, and settings slices.
      </p>
    </AppFrame>
  );
}
