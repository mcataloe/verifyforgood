import { useMemo, useState } from "react";
import { Button, Stack, TextInput } from "@mantine/core";
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
import { PortalActionGroup } from "../components/PortalPrimitives";

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
            onSubmit={(event) => {
              event.preventDefault();
              const nextRows = searchCustomerOrganizationsByEin(einQuery);
              setRows(nextRows);
              setSelectedEin(nextRows[0]?.ein ?? null);
              setHasSearched(true);
            }}
          >
            <Stack maw={540}>
              <TextInput
                aria-label="EIN"
                label="EIN"
                onChange={(event) => {
                  setEinQuery(event.target.value);
                }}
                placeholder="12-3456789"
                value={einQuery}
              />

              <PortalActionGroup>
                <Button disabled={!einQuery.trim()} type="submit">
                  By EIN
                </Button>
              </PortalActionGroup>
            </Stack>
          </form>
        ) : (
          <form
            onSubmit={(event) => {
              event.preventDefault();
              const nextRows =
                searchCustomerOrganizationsByAddress(addressQuery);
              setRows(nextRows);
              setSelectedEin(nextRows[0]?.ein ?? null);
              setHasSearched(true);
            }}
          >
            <Stack maw={540}>
              <TextInput
                aria-label="Address"
                label="Address"
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    address: event.target.value,
                  }));
                }}
                placeholder="431 Mission Street"
                value={addressQuery.address}
              />

              <TextInput
                aria-label="City"
                label="City"
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    city: event.target.value,
                  }));
                }}
                placeholder="San Francisco"
                value={addressQuery.city}
              />

              <TextInput
                aria-label="State"
                label="State"
                maxLength={2}
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    state: event.target.value,
                  }));
                }}
                placeholder="CA"
                value={addressQuery.state}
              />

              <TextInput
                aria-label="Zip"
                label="Zip"
                onChange={(event) => {
                  setAddressQuery((current) => ({
                    ...current,
                    zip: event.target.value,
                  }));
                }}
                placeholder="94105"
                value={addressQuery.zip}
              />

              <PortalActionGroup>
                <Button disabled={!hasAddressSearchInput(addressQuery)} type="submit">
                  By Address
                </Button>
              </PortalActionGroup>
            </Stack>
          </form>
        )}
      </PortalDetailSection>

      {hasSearched ? (
        <PortalDetailSection
          intro="Sort and review the results before opening an organization record."
          title="Results"
        >
          {mappedRows.length === 0 ? (
            <EmptyState
              description="Adjust your search and try again."
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
                    <Button
                      onClick={() => {
                        setSelectedEin(row.ein);
                      }}
                      size="xs"
                      type="button"
                      variant="light"
                    >
                      View details
                    </Button>
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
          intro="Review the available details for this organization."
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
