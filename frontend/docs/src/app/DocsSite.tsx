import { readRuntimeConfig } from "@charity-status/shared-config";
import type { FrontendAppInfo } from "@charity-status/shared-types";
import { DocsLayout } from "../components/DocsLayout";
import { ApiUsagePage } from "../pages/ApiUsagePage";
import { FaqPage } from "../pages/FaqPage";
import { GettingStartedPage } from "../pages/GettingStartedPage";
import { IntegrationsPage } from "../pages/IntegrationsPage";
import { ProductOverviewPage } from "../pages/ProductOverviewPage";
import { docsEndpoints } from "./docsEndpoints";
import { docsRoutes, useDocsRoute } from "./docsRoutes";

const appInfo: FrontendAppInfo = {
  audience: "Customers, developers, and internal operators referencing product and API guidance.",
  description:
    "Content-focused documentation shell for product overview, API onboarding, integration examples, and support-oriented reference.",
  title: "VerifyForGood documentation shell",
  surface: "docs",
};

export function DocsSite() {
  const runtimeConfig = readRuntimeConfig(import.meta.env);
  const currentRoute = useDocsRoute();
  const endpoints = docsEndpoints(runtimeConfig);

  return (
    <DocsLayout
      app={appInfo}
      currentRoute={currentRoute}
      routes={docsRoutes}
      runtimeConfig={runtimeConfig}
    >
      {currentRoute.key === "getting-started" ? (
        <GettingStartedPage endpoints={endpoints} runtimeConfig={runtimeConfig} />
      ) : null}
      {currentRoute.key === "product-overview" ? <ProductOverviewPage /> : null}
      {currentRoute.key === "api-usage" ? (
        <ApiUsagePage endpoints={endpoints} runtimeConfig={runtimeConfig} />
      ) : null}
      {currentRoute.key === "integrations" ? <IntegrationsPage /> : null}
      {currentRoute.key === "faq" ? <FaqPage /> : null}
    </DocsLayout>
  );
}
