import { useMemo, useState } from "react";
import {
  DataTable,
  EmptyState,
  type DataTableColumn,
} from "@charity-status/shared-ui";
import {
  getCustomerUserOrganizationDetail,
  searchCustomerOrganizationsByAddress,
  searchCustomerOrganizationsByEin,
  type CustomerUserAddressSearchInput,
  type CustomerUserOrganizationRecord,
} from "./customerUserOrganizations";
import { PortalNonprofitEmbeddedDetail } from "../nonprofits/PortalNonprofitDetailView";
import {
  PortalDetailSection,
  PortalDetailView,
} from "../components/PortalDetailView";

interface CustomerUserSearchPageProps {
  pane: "search-address" | "search-ein";
}

type SearchResultRow = {
  address: string;
  city: string;
  ein: string;
  name: string;
  state: string;
  zip: string;
};

const resultColumns: DataTableColumn<SearchResultRow>[] = [
  {
    key: "name",
    header: "Organization",
    render: (row) => row.name,
    sortable: true,
    sortValue: (row) => row.name,
  },
  {
    key: "ein",
    header: "EIN",
    render: (row) => row.ein,
  },
  {
    key: "city",
    header: "City",
    render: (row) => row.city,
    sortable: true,
    sortValue: (row) => row.city,
  },
  {
    key: "state",
    header: "State",
    render: (row) => row.state,
    sortable: true,
    sortValue: (row) => row.state,
  },
  {
    key: "zip",
    header: "Zip",
    render: (row) => row.zip,
    sortable: true,
    sortValue: (row) => row.zip,
  },
];

export function CustomerUserSearchPage({ pane }: CustomerUserSearchPageProps) {
  const [einQuery, setEinQuery] = useState("");
  const [addressQuery, setAddressQuery] =
    useState<CustomerUserAddressSearchInput>({
      address: "",
      city: "",
      state: "",
      zip: "",
    });
  const [rows, setRows] = useState<CustomerUserOrganizationRecord[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedEin, setSelectedEin] = useState<string | null>(null);

  const title = pane === "search-ein" ? "By EIN" : "By Address";
  const description =
    pane === "search-ein"
      ? "Run an exact EIN lookup and sort any returned candidates by city, state, or zip before opening the organization record."
      : "Use any combination of address, city, state, or zip to discover organizations and sort the resulting candidate list.";

  const mappedRows = useMemo<SearchResultRow[]>(
    () =>
      rows.map((record) => ({
        address: record.address,
        city: record.city,
        ein: record.ein,
        name: record.name,
        state: record.detail.state,
        zip: record.zip,
      })),
    [rows],
  );
  const selectedDetail = selectedEin
    ? getCustomerUserOrganizationDetail(selectedEin)
    : null;

  return (
    <PortalDetailView eyebrow="Search" intro={description} title={title}>
      <PortalDetailSection
        intro={
          pane === "search-ein"
            ? "Exact EIN lookup with sortable location fields in the results list."
            : "Address discovery that accepts partial location input and keeps the results sortable."
        }
        title="Lookup"
      >
        {pane === "search-ein" ? (
          <form
            className="portal-form"
            onSubmit={(event) => {
              event.preventDefault();
              const nextRows = searchCustomerOrganizationsByEin(einQuery);
              setRows(nextRows);
              setSelectedEin(nextRows[0]?.ein ?? null);
              setHasSearched(true);
            }}
          >
            <label className="portal-form__field">
              <span>EIN</span>
              <input
                aria-label="EIN"
                className="portal-form__input"
                onChange={(event) => {
                  setEinQuery(event.target.value);
                }}
                placeholder="12-3456789"
                type="text"
                value={einQuery}
              />
            </label>

            <div className="portal-form__actions">
              <button
                className="portal-shell__action portal-shell__action--primary"
                disabled={!einQuery.trim()}
                type="submit"
              >
                By EIN
              </button>
            </div>
          </form>
        ) : (
          <form
            className="portal-form portal-form--detail"
            onSubmit={(event) => {
              event.preventDefault();
              const nextRows =
                searchCustomerOrganizationsByAddress(addressQuery);
              setRows(nextRows);
              setSelectedEin(nextRows[0]?.ein ?? null);
              setHasSearched(true);
            }}
          >
            <label className="portal-form__field">
              <span>Address</span>
              <input
                aria-label="Address"
                className="portal-form__input"
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    address: event.target.value,
                  }));
                }}
                placeholder="431 Mission Street"
                type="text"
                value={addressQuery.address}
              />
            </label>

            <label className="portal-form__field">
              <span>City</span>
              <input
                aria-label="City"
                className="portal-form__input"
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    city: event.target.value,
                  }));
                }}
                placeholder="San Francisco"
                type="text"
                value={addressQuery.city}
              />
            </label>

            <label className="portal-form__field">
              <span>State</span>
              <input
                aria-label="State"
                className="portal-form__input"
                maxLength={2}
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    state: event.target.value,
                  }));
                }}
                placeholder="CA"
                type="text"
                value={addressQuery.state}
              />
            </label>

            <label className="portal-form__field">
              <span>Zip</span>
              <input
                aria-label="Zip"
                className="portal-form__input"
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    zip: event.target.value,
                  }));
                }}
                placeholder="94105"
                type="text"
                value={addressQuery.zip}
              />
            </label>

            <div className="portal-form__actions portal-form__actions--full">
              <button
                className="portal-shell__action portal-shell__action--primary"
                disabled={!hasAddressSearchInput(addressQuery)}
                type="submit"
              >
                By Address
              </button>
            </div>
          </form>
        )}
      </PortalDetailSection>

      {hasSearched ? (
        <PortalDetailSection
          intro="Use the sortable city, state, and zip columns before opening the organization review pane."
          title="Results"
        >
          {mappedRows.length === 0 ? (
            <EmptyState
              description="Adjust the current query and try again. These panes are backed by a local placeholder dataset in this phase."
              title={`No organizations matched this ${pane === "search-ein" ? "EIN" : "address"} search`}
            />
          ) : (
            <DataTable
              columns={[
                ...resultColumns,
                {
                  key: "actions",
                  header: "Actions",
                  render: (row) => (
                    <button
                      className="portal-shell__action"
                      onClick={() => {
                        setSelectedEin(row.ein);
                      }}
                      type="button"
                    >
                      View details
                    </button>
                  ),
                },
              ]}
              getSearchText={(row) =>
                `${row.name} ${row.ein} ${row.address} ${row.city} ${row.state} ${row.zip}`
              }
              initialSort={{ columnKey: "city", direction: "asc" }}
              rows={mappedRows}
              searchPlaceholder="Filter returned organizations"
            />
          )}
        </PortalDetailSection>
      ) : null}

      {selectedDetail ? (
        <PortalDetailSection
          intro="Organization detail remains placeholder-backed in this phase."
          title="Organization details"
        >
          <PortalNonprofitEmbeddedDetail detail={selectedDetail} />
        </PortalDetailSection>
      ) : null}
    </PortalDetailView>
  );
}

function hasAddressSearchInput(input: CustomerUserAddressSearchInput) {
  return Boolean(
    input.address?.trim() ||
    input.city?.trim() ||
    input.state?.trim() ||
    input.zip?.trim(),
  );
}
