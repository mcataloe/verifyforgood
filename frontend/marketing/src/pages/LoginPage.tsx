import { CallToAction, FeatureGrid } from "@charity-status/shared-ui";

export function LoginPage({
  platformLoginUrl,
}: {
  platformLoginUrl: string;
}) {
  return (
    <div className="marketing-page-stack">
      <CallToAction
        actions={
          <>
            <a className="marketing-shell__cta marketing-shell__cta--primary" href={platformLoginUrl}>
              Continue to portal
            </a>
            <a className="marketing-shell__cta marketing-shell__cta--secondary" href="#/contact">
              Talk to the team
            </a>
          </>
        }
        description="The public site keeps login as a clear handoff into the authenticated application so public messaging and protected workflows can evolve independently."
        title="Portal entry point"
      />

      <FeatureGrid
        items={[
          {
            title: "Public content stays crawlable",
            description:
              "Marketing pages remain conversion-oriented and free of authenticated runtime assumptions.",
          },
          {
            title: "Protected workflows stay in the portal",
            description:
              "Organization review, onboarding, API access, and billing remain inside the dedicated platform surface.",
          },
        ]}
      />
    </div>
  );
}
