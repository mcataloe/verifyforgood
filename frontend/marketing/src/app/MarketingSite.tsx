import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { MarketingLayout } from "../components/MarketingLayout";
import { ContactPage } from "../pages/ContactPage";
import { DevelopersPage } from "../pages/DevelopersPage";
import { HomePage } from "../pages/HomePage";
import { LoginPage } from "../pages/LoginPage";
import { PricingPage } from "../pages/PricingPage";
import { ProductPage } from "../pages/ProductPage";
import { TrustPage } from "../pages/TrustPage";
import { marketingEndpoints } from "./marketingEndpoints";
import { marketingRoutes, useMarketingRoute } from "./marketingRoutes";

const appInfo: FrontendAppInfo = {
  audience: "Public visitors, prospects, and future partner referrals.",
  description:
    "Public-facing site shell for product messaging, trust-building, developer onboarding, and future conversion flows.",
  title: "VerifyForGood public site shell",
  surface: "marketing",
};

export function MarketingSite() {
  const runtimeConfig = readRuntimeConfig(import.meta.env);
  const currentRoute = useMarketingRoute();
  const endpoints = marketingEndpoints(runtimeConfig);

  return (
    <MarketingLayout
      app={appInfo}
      currentRoute={currentRoute}
      routes={marketingRoutes}
      runtimeConfig={runtimeConfig}
    >
      {currentRoute.key === "home" ? (
        <HomePage endpoints={endpoints} runtimeConfig={runtimeConfig} />
      ) : null}
      {currentRoute.key === "product" ? <ProductPage /> : null}
      {currentRoute.key === "pricing" ? <PricingPage /> : null}
      {currentRoute.key === "trust" ? <TrustPage /> : null}
      {currentRoute.key === "developers" ? (
        <DevelopersPage endpoints={endpoints} runtimeConfig={runtimeConfig} />
      ) : null}
      {currentRoute.key === "contact" ? <ContactPage /> : null}
      {currentRoute.key === "login" ? <LoginPage /> : null}
    </MarketingLayout>
  );
}
