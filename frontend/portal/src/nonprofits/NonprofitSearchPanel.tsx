import { useState } from "react";
import { Grid, Inline, Panel } from "@charity-status/shared-ui";
import {
  PortalEmptyState,
  PortalLoadingState,
  PortalNotice,
} from "../components/feedback";
import { usePortalOrganization } from "../organization/usePortalOrganization";
import {
  usePortalNonprofitSearch,
  type PortalNonprofitSearchController,
} from "./usePortalNonprofitSearch";

interface NonprofitSearchPanelProps {
  controller?: PortalNonprofitSearchController;
}

export function NonprofitSearchPanel({
  controller,
}: NonprofitSearchPanelProps) {
  const organization = usePortalOrganization();
  const defaultController = usePortalNonprofitSearch();
  const search = controller ?? defaultController;
  const [query, setQuery] = useState("");

  return (
    <Grid className="portal-page-grid">
      <Panel
        title="Nonprofit verification search"
        subtitle="Search by EIN for an exact lookup or by organization name for a lightweight listing."
      >
        <p>
          This is the portal's core product interaction. Requests run through
          the organization-scoped portal API client for{" "}
          <strong>{organization.activeOrganization.organization_name}</strong>.
        </p>

        <form
          className="portal-form"
          onSubmit={(event) => {
            event.preventDefault();
            void search.runSearch(query);
          }}
        >
          <label className="portal-form__field">
            <span>Search query</span>
            <input
              className="portal-form__input"
              name="query"
              onChange={(event) => {
                setQuery(event.target.value);
              }}
              placeholder="12-3456789 or Helping Hands Foundation"
              type="text"
              value={query}
            />
          </label>

          <Inline className="portal-form__actions">
            <button
              className="portal-shell__action portal-shell__action--primary"
              disabled={search.isLoading || !query.trim()}
              type="submit"
            >
              {search.isLoading ? "Searching..." : "Search nonprofit"}
            </button>
          </Inline>
        </form>

        <dl className="portal-shell__details">
          <div>
            <dt>Search mode</dt>
            <dd>{search.searchMode ?? "Not run yet"}</dd>
          </div>
          <div>
            <dt>Last query</dt>
            <dd>{search.lastQuery || "None"}</dd>
          </div>
          <div>
            <dt>Workspace</dt>
            <dd>{organization.activeOrganization.workspace_id}</dd>
          </div>
        </dl>

        {search.error ? (
          <PortalNotice tone="error">
            <p>{search.error}</p>
          </PortalNotice>
        ) : null}
      </Panel>

      {search.isLoading ? (
        <PortalLoadingState
          subtitle="Waiting on the backend nonprofit endpoints."
          title="Loading nonprofit results"
        >
          <p>Running the current lookup through the portal API client.</p>
        </PortalLoadingState>
      ) : null}

      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "ein" &&
      !search.detail ? (
        <PortalEmptyState
          subtitle="The exact EIN lookup returned no matching organization."
          title="No nonprofit found"
        >
          <p>
            Try another EIN or switch to a name-based search if you are still
            narrowing the candidate organization.
          </p>
        </PortalEmptyState>
      ) : null}

      {search.hasSearched &&
      !search.isLoading &&
      !search.error &&
      search.searchMode === "name" &&
      search.results.length === 0 ? (
        <PortalEmptyState
          subtitle="The current name query returned an empty result set."
          title="No nonprofit matches"
        >
          <p>
            Try broadening the organization name or run an exact EIN lookup for
            a more deterministic result.
          </p>
        </PortalEmptyState>
      ) : null}

      {search.results.length > 0 ? (
        <Panel
          title="Search results"
          subtitle="Select a result to load the full nonprofit verification detail."
        >
          <div className="portal-result-list">
            {search.results.map((result) => (
              <article
                className="portal-result-card"
                key={`${result.ein}-${result.name}`}
              >
                <div className="portal-result-card__header">
                  <div>
                    <h3>{result.name}</h3>
                    <p>
                      {result.ein} | {result.state}
                    </p>
                  </div>
                  <span className="portal-key-chip">
                    {result.active === null
                      ? result.irsStatus
                      : result.active
                        ? "active"
                        : "inactive"}
                  </span>
                </div>

                <dl className="portal-shell__details">
                  <div>
                    <dt>IRS status</dt>
                    <dd>{result.irsStatus}</dd>
                  </div>
                  <div>
                    <dt>Subsection</dt>
                    <dd>{result.subsection}</dd>
                  </div>
                  <div>
                    <dt>Tax period</dt>
                    <dd>{result.taxPeriod}</dd>
                  </div>
                </dl>

                <Inline className="portal-form__actions">
                  <button
                    className="portal-shell__action"
                    onClick={() => {
                      void search.viewResultDetail(result.ein);
                    }}
                    type="button"
                  >
                    View details
                  </button>
                </Inline>
              </article>
            ))}
          </div>
        </Panel>
      ) : null}

      {search.detail ? (
        <Panel
          title="Verification result"
          subtitle="Detailed nonprofit lookup with filing and model metadata."
        >
          <div className="portal-result-detail">
            <div>
              <p className="portal-shell__eyebrow">Organization</p>
              <h3>{search.detail.name}</h3>
              <p>
                {search.detail.ein} | {search.detail.state}
              </p>
            </div>

            <dl className="portal-shell__details">
              <div>
                <dt>IRS status</dt>
                <dd>{search.detail.irsStatus}</dd>
              </div>
              <div>
                <dt>Entity type</dt>
                <dd>{search.detail.entityType}</dd>
              </div>
              <div>
                <dt>Tax deductible</dt>
                <dd>{search.detail.taxDeductible}</dd>
              </div>
              <div>
                <dt>NTEE category</dt>
                <dd>{search.detail.nteeCategory}</dd>
              </div>
              <div>
                <dt>Recent 990 on file</dt>
                <dd>{search.detail.recent990OnFile}</dd>
              </div>
              <div>
                <dt>Filing form</dt>
                <dd>{search.detail.filingFormType}</dd>
              </div>
              <div>
                <dt>Filing year</dt>
                <dd>{search.detail.filingTaxYear}</dd>
              </div>
              <div>
                <dt>Filing date</dt>
                <dd>{search.detail.filingDate}</dd>
              </div>
              <div>
                <dt>Parse status</dt>
                <dd>{search.detail.filingParseStatus}</dd>
              </div>
              <div>
                <dt>Known filings</dt>
                <dd>{String(search.detail.filingsCount)}</dd>
              </div>
              <div>
                <dt>Subsection</dt>
                <dd>{search.detail.subsection}</dd>
              </div>
              <div>
                <dt>Tax period</dt>
                <dd>{search.detail.taxPeriod}</dd>
              </div>
              <div>
                <dt>Model source</dt>
                <dd>{search.detail.modelSource}</dd>
              </div>
              <div>
                <dt>Model version</dt>
                <dd>{search.detail.modelVersion}</dd>
              </div>
              <div>
                <dt>Query execution</dt>
                <dd>{search.detail.queryExecutionId}</dd>
              </div>
            </dl>
          </div>
        </Panel>
      ) : null}
    </Grid>
  );
}
