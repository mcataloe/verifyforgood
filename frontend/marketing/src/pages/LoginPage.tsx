import { Grid, Panel } from "@charity-status/shared-ui";

export function LoginPage() {
  return (
    <Grid className="marketing-page-grid">
      <Panel title="Portal entry point" subtitle="Public-site handoff into the separate authenticated product surface.">
        <p>
          The public site keeps login as a simple handoff page rather than embedding authenticated
          runtime assumptions. A future deployed marketing environment can point this area at the
          standalone portal runtime once its base URL is finalized.
        </p>
      </Panel>

      <Panel title="Why this stays separate" subtitle="Marketing and portal concerns should not collapse into one runtime path by default.">
        <ul className="marketing-list">
          <li>Public content remains crawlable and conversion-oriented.</li>
          <li>Authenticated workflows stay in the portal application.</li>
          <li>Auth provider choices can evolve without forcing public-site rewrites.</li>
        </ul>
      </Panel>
    </Grid>
  );
}
