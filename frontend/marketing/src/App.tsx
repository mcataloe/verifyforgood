import { VerifyForGoodMantineProvider } from "@charity-status/shared-ui";
import { MarketingSite } from "./app/MarketingSite";

export function App() {
  return (
    <VerifyForGoodMantineProvider>
      <MarketingSite />
    </VerifyForGoodMantineProvider>
  );
}
