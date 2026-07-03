import {
  normalizeEinQuery,
  type PortalNonprofitDetail,
} from "../nonprofits/nonprofitSearch";

export interface CustomerUserOrganizationRecord {
  address: string;
  city: string;
  detail: PortalNonprofitDetail;
  ein: string;
  name: string;
  zip: string;
}

export interface CustomerUserAddressSearchInput {
  address?: string;
  city?: string;
  state?: string;
  zip?: string;
}

export function searchCustomerOrganizationsByEin(
  query: string,
): CustomerUserOrganizationRecord[] {
  const normalizedEin = normalizeEinQuery(query);

  if (!normalizedEin) {
    return [];
  }

  return customerUserOrganizationRecords.filter(
    (record) => record.ein.replaceAll("-", "") === normalizedEin,
  );
}

export function searchCustomerOrganizationsByAddress(
  input: CustomerUserAddressSearchInput,
): CustomerUserOrganizationRecord[] {
  const normalizedInput = {
    address: normalizeText(input.address),
    city: normalizeText(input.city),
    state: normalizeText(input.state),
    zip: normalizeText(input.zip),
  };

  if (
    !normalizedInput.address &&
    !normalizedInput.city &&
    !normalizedInput.state &&
    !normalizedInput.zip
  ) {
    return [];
  }

  return customerUserOrganizationRecords.filter((record) => {
    if (
      normalizedInput.address &&
      !normalizeText(record.address).includes(normalizedInput.address)
    ) {
      return false;
    }

    if (
      normalizedInput.city &&
      !normalizeText(record.city).includes(normalizedInput.city)
    ) {
      return false;
    }

    if (
      normalizedInput.state &&
      !normalizeText(record.detail.state).includes(normalizedInput.state)
    ) {
      return false;
    }

    if (
      normalizedInput.zip &&
      !normalizeText(record.zip).includes(normalizedInput.zip)
    ) {
      return false;
    }

    return true;
  });
}

export function getCustomerUserOrganizationDetail(
  ein: string,
): PortalNonprofitDetail | null {
  return (
    customerUserOrganizationRecords.find((record) => record.ein === ein)
      ?.detail ?? null
  );
}

function normalizeText(value: string | undefined) {
  return String(value || "")
    .trim()
    .toLowerCase();
}

const customerUserOrganizationRecords: CustomerUserOrganizationRecord[] = [
  createRecord({
    address: "431 Mission Street",
    city: "San Francisco",
    ein: "13-1635294",
    filingDate: "2025-11-14",
    filingTaxYear: "2024",
    irsStatus: "Active",
    name: "American National Red Cross",
    nteeCategory: "P20 Human Service Organizations",
    zip: "94105",
  }),
  createRecord({
    address: "35 East Wacker Drive",
    city: "Chicago",
    ein: "36-3673599",
    filingDate: "2025-09-03",
    filingTaxYear: "2024",
    irsStatus: "Active",
    name: "Feeding America",
    nteeCategory: "K31 Food Banks and Food Distribution",
    zip: "60601",
  }),
  createRecord({
    address: "807 North Campbell Station Road",
    city: "Knoxville",
    ein: "58-1931921",
    filingDate: "2025-08-19",
    filingTaxYear: "2024",
    irsStatus: "Active",
    name: "Community Housing Partners",
    nteeCategory: "L20 Housing Development and Management",
    state: "TN",
    zip: "37932",
  }),
  createRecord({
    address: "4600 East West Highway",
    city: "Bethesda",
    ein: "53-0196605",
    filingDate: "2025-07-10",
    filingTaxYear: "2024",
    irsStatus: "Active",
    name: "The Nature Conservancy",
    nteeCategory: "C30 Natural Resources Conservation",
    state: "MD",
    zip: "20814",
  }),
  createRecord({
    address: "2201 Broadway",
    city: "Oakland",
    ein: "94-2681680",
    filingDate: "2025-10-22",
    filingTaxYear: "2024",
    irsStatus: "Active",
    name: "East Bay Community Foundation",
    nteeCategory: "T31 Community Foundations",
    zip: "94612",
  }),
];

function createRecord(input: {
  address: string;
  city: string;
  ein: string;
  filingDate: string;
  filingTaxYear: string;
  irsStatus: string;
  name: string;
  nteeCategory: string;
  state?: string;
  zip: string;
}): CustomerUserOrganizationRecord {
  const state = input.state ?? inferStateFromZip(input.zip);

  return {
    address: input.address,
    city: input.city,
    ein: input.ein,
    name: input.name,
    zip: input.zip,
    detail: {
      appearsBecause: [
        "Matched a placeholder customer-user organization record.",
      ],
      complianceCheckType: "No compliance snapshot",
      complianceCheckedAt: "Unavailable",
      complianceStatus: "No compliance snapshot",
      dataGaps: [],
      ein: input.ein,
      entityType: "Public charity",
      filingDate: input.filingDate,
      filingFormType: "990",
      filingParseStatus: "Parsed",
      filingTaxYear: input.filingTaxYear,
      filingsCount: 6,
      highlights: [
        "Recent filing details are available in this placeholder record.",
      ],
      irsStatus: input.irsStatus,
      modelSource: "customer_user_placeholder_search",
      modelVersion: "2026-03-23",
      name: input.name,
      nteeCategory: input.nteeCategory,
      queryExecutionId: `mock_${input.ein.replaceAll("-", "")}`,
      recent990OnFile: "true",
      riskIndicators: [],
      review: null,
      snapshotMaterializedAt: "2026-03-23T00:00:00+00:00",
      sourceAvailability: [],
      sourceSummaries: [],
      state,
      subsection: "501(c)(3)",
      taxDeductible: "true",
      taxPeriod: `${input.filingTaxYear}-12`,
    },
  };
}

function inferStateFromZip(zip: string) {
  if (zip.startsWith("94")) {
    return "CA";
  }

  if (zip.startsWith("60")) {
    return "IL";
  }

  return "NY";
}
