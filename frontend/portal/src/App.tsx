import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { PortalApp } from "./app/PortalApp";

export function App() {
  return (
    <VerifyForGoodMantineProvider>
      <PortalApp />
    </VerifyForGoodMantineProvider>
  );
}
