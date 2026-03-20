export type FrontendSurface = "marketing" | "portal";

export interface FrontendAppInfo {
  surface: FrontendSurface;
  title: string;
  description: string;
  audience: string;
}
