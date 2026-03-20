import { Panel } from "@charity-status/shared-ui";

export function ContactPage() {
  return (
    <div className="marketing-page-grid">
      <Panel title="Contact and demo" subtitle="This area should support both sales motion and self-serve conversion.">
        <ul className="marketing-list">
          <li>Future demo request flow.</li>
          <li>Support and trust escalation path.</li>
          <li>Conversion handoff into trial, pricing, and developer onboarding journeys.</li>
        </ul>
      </Panel>

      <Panel title="Intentionally deferred" subtitle="Not choosing a CMS, CRM, or form workflow yet.">
        <ul className="marketing-list">
          <li>No embedded form system in this phase.</li>
          <li>No analytics or attribution stack yet.</li>
          <li>No public docs runtime or blog assumptions yet.</li>
        </ul>
      </Panel>
    </div>
  );
}
