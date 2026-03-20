import { useEffect, useState } from "react";

export interface MarketingRouteDefinition {
  key: "home" | "product" | "pricing" | "trust" | "developers" | "contact" | "login";
  description: string;
  hash: string;
  label: string;
}

export const marketingRoutes: MarketingRouteDefinition[] = [
  {
    key: "home",
    label: "Home",
    hash: "#/home",
    description: "Product framing, trust cues, and primary calls to action.",
  },
  {
    key: "product",
    label: "Product",
    hash: "#/product",
    description: "What customers can do with verification, source inspection, and monitoring.",
  },
  {
    key: "pricing",
    label: "Pricing",
    hash: "#/pricing",
    description: "Plan structure and conversion guidance without locking in published prices here.",
  },
  {
    key: "trust",
    label: "Security & Trust",
    hash: "#/trust",
    description: "Reliability, deterministic scoring, and hosted billing/security posture.",
  },
  {
    key: "developers",
    label: "Developers",
    hash: "#/developers",
    description: "API-oriented onboarding, auth modes, and integration entry points.",
  },
  {
    key: "contact",
    label: "Contact & Demo",
    hash: "#/contact",
    description: "Human contact, sales motion, and future conversion paths.",
  },
  {
    key: "login",
    label: "Login",
    hash: "#/login",
    description: "Entry point for the separate authenticated portal surface.",
  },
];

const defaultRoute = marketingRoutes[0];

export function resolveMarketingRoute(hash: string): MarketingRouteDefinition {
  const candidate = hash.trim() || defaultRoute.hash;
  return marketingRoutes.find((route) => route.hash === candidate) ?? defaultRoute;
}

export function useMarketingRoute(): MarketingRouteDefinition {
  const [route, setRoute] = useState<MarketingRouteDefinition>(() =>
    resolveMarketingRoute(window.location.hash),
  );

  useEffect(() => {
    if (!window.location.hash) {
      window.location.hash = defaultRoute.hash;
    }

    const handleHashChange = () => {
      setRoute(resolveMarketingRoute(window.location.hash));
    };

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  return route;
}
