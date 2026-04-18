import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { PortalApp } from "./app/PortalApp";
import { PortalToastProvider } from "./components/feedback";

export function App() {
  return (
    <VerifyForGoodMantineProvider>
      <PortalToastProvider>
        <PortalApp />
      </PortalToastProvider>
    </VerifyForGoodMantineProvider>
  );
}
