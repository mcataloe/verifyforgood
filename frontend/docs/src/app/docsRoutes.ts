import { useEffect, useState } from "react";

export interface DocsRouteDefinition {
  key: "getting-started" | "product-overview" | "api-usage" | "integrations" | "faq";
  description: string;
  hash: string;
  label: string;
}

export const docsRoutes: DocsRouteDefinition[] = [
  {
    key: "getting-started",
    label: "Getting Started",
    hash: "#/getting-started",
    description: "High-level onboarding for customers and developers entering the product for the first time.",
  },
  {
    key: "product-overview",
    label: "Product Overview",
    hash: "#/product-overview",
    description: "Core capability map for verification, scoring, source inspection, and customer-managed settings.",
  },
  {
    key: "api-usage",
    label: "API Usage",
    hash: "#/api-usage",
    description: "Versioning, auth modes, and early endpoint guidance grounded in the current API contract.",
  },
  {
    key: "integrations",
    label: "Integrations",
    hash: "#/integrations",
    description: "Examples and reference stubs for workflow integrations such as M365 Power Automate.",
  },
  {
    key: "faq",
    label: "FAQ",
    hash: "#/faq",
    description: "Support-oriented answers for common adoption, billing, and platform questions.",
  },
];

const defaultRoute = docsRoutes[0];

export function resolveDocsRoute(hash: string): DocsRouteDefinition {
  const candidate = hash.trim() || defaultRoute.hash;
  return docsRoutes.find((route) => route.hash === candidate) ?? defaultRoute;
}

export function useDocsRoute(): DocsRouteDefinition {
  const [route, setRoute] = useState<DocsRouteDefinition>(() =>
    resolveDocsRoute(window.location.hash),
  );

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = defaultRoute.hash;
    }

    const handleHashChange = () => {
      setRoute(resolveDocsRoute(window.location.hash));
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  return route;
}
