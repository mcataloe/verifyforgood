import {
  Box,
  Button,
  Group,
  Pagination,
  Stack,
  Table,
  Text,
  UnstyledButton,
} from "@mantine/core";
import {
  IconChevronDown,
  IconChevronUp,
  IconSelector,
} from "@tabler/icons-react";
import { useMemo, useState, type ReactNode } from "react";
import { useVerifyForGoodSemanticColors } from "../../theme/useVerifyForGoodTheme";
import { verifyForGoodTokens } from "../../theme/tokens";
import { EmptyState } from "../EmptyState";
import { LoadingSkeleton } from "../LoadingSkeleton";
import { FilterBar, type FilterBarOption } from "./FilterBar";

type SortDirection = "asc" | "desc";

export type DataTableColumn<T> = {
  align?: "left" | "center" | "right";
  header: ReactNode;
  key: string;
  render?: (row: T, index: number) => ReactNode;
  sortable?: boolean;
  sortValue?: (row: T) => string | number;
  value?: (row: T, index: number) => ReactNode;
  width?: string;
};

export type DataTableFilterDefinition<T> = {
  getValue: (row: T) => string;
  key: string;
  label: string;
  options: FilterBarOption[];
};

type DataTableProps<T> = {
  ariaLabel?: string;
  caption?: ReactNode;
  columns: DataTableColumn<T>[];
  emptyState?: ReactNode;
  filterDefinitions?: DataTableFilterDefinition<T>[];
  getSearchText?: (row: T) => string;
  initialSort?: { columnKey: string; direction?: SortDirection };
  loading?: boolean;
  loadingDescription?: ReactNode;
  loadingTitle?: ReactNode;
  noResultsState?: ReactNode;
  pageSize?: number;
  rowKey?: (row: T, index: number) => string;
  rows: T[];
  searchLabel?: string;
  searchPlaceholder?: string;
};

/**
 * Shared interactive data table for entity-heavy portal screens.
 */
export function DataTable<T>({
  ariaLabel = "Data table",
  caption,
  columns,
  emptyState,
  filterDefinitions = [],
  getSearchText,
  initialSort,
  loading = false,
  loadingDescription,
  loadingTitle,
  noResultsState,
  pageSize = 6,
  rowKey,
  rows,
  searchLabel = "Search rows",
  searchPlaceholder = "Search records",
}: DataTableProps<T>) {
  const { semantic } = useVerifyForGoodSemanticColors();
  const [searchValue, setSearchValue] = useState("");
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState<Record<string, string>>(
    Object.fromEntries(filterDefinitions.map((filter) => [filter.key, "all"])),
  );
  const [sortState, setSortState] = useState<{
    columnKey: string;
    direction: SortDirection;
  } | null>(
    initialSort
      ? {
          columnKey: initialSort.columnKey,
          direction: initialSort.direction ?? "asc",
        }
      : null,
  );

  const filteredRows = useMemo(() => {
    const normalizedQuery = searchValue.trim().toLowerCase();

    const searchedRows =
      normalizedQuery && getSearchText
        ? rows.filter((row) =>
            getSearchText(row).toLowerCase().includes(normalizedQuery),
          )
        : rows;

    const result = searchedRows.filter((row) =>
      filterDefinitions.every((filter) => {
        const filterValue = filters[filter.key] ?? "all";
        return filterValue === "all" || filter.getValue(row) === filterValue;
      }),
    );

    if (!sortState) {
      return result;
    }

    const sortColumn = columns.find(
      (column) => column.key === sortState.columnKey,
    );
    if (!sortColumn || !sortColumn.sortable) {
      return result;
    }

    const direction = sortState.direction === "asc" ? 1 : -1;

    return [...result].sort((left, right) => {
      const leftValue = getColumnSortValue(sortColumn, left);
      const rightValue = getColumnSortValue(sortColumn, right);

      if (leftValue === rightValue) {
        return 0;
      }

      return leftValue > rightValue ? direction : -direction;
    });
  }, [columns, filterDefinitions, filters, getSearchText, rows, searchValue, sortState]);

  const totalPages = Math.max(1, Math.ceil(filteredRows.length / pageSize));
  const currentPage = Math.min(page, totalPages);
  const pageStartIndex = (currentPage - 1) * pageSize;
  const pagedRows = filteredRows.slice(
    pageStartIndex,
    currentPage * pageSize,
  );

  const hasFilterSurface = Boolean(getSearchText || filterDefinitions.length);
  const isFiltered =
    Boolean(searchValue.trim()) ||
    Object.values(filters).some((value) => value !== "all");

  const clearFilters = () => {
    setFilters(
      Object.fromEntries(filterDefinitions.map((filter) => [filter.key, "all"])),
    );
    setPage(1);
    setSearchValue("");
    setSortState(
      initialSort
        ? {
            columnKey: initialSort.columnKey,
            direction: initialSort.direction ?? "asc",
          }
        : null,
    );
  };

  if (loading) {
    return (
      <LoadingSkeleton
        description={loadingDescription}
        rows={Math.min(pageSize, 5)}
        title={loadingTitle}
        variant="table"
      />
    );
  }

  if (!rows.length) {
    return emptyState ? (
      <>{emptyState}</>
    ) : (
      <EmptyState
        description="Records will appear here once data is available."
        title="No records yet"
      />
    );
  }

  return (
    <Stack gap="md">
      <Box
        style={{
          backgroundColor: semantic.surface,
          border: `1px solid ${semantic.border}`,
          borderRadius: verifyForGoodTokens.radius.card,
          overflow: "hidden",
        }}
      >
        {hasFilterSurface ? (
          <Box
            px="md"
            py="md"
            style={{
              backgroundColor: semantic.surface,
              borderBottom: `1px solid ${semantic.border}`,
            }}
          >
            <Stack gap="sm">
              <Group justify="space-between" wrap="wrap">
                <Text c="dimmed" fz="sm">
                  {filteredRows.length} record{filteredRows.length === 1 ? "" : "s"}
                </Text>
                {isFiltered ? (
                  <Button onClick={clearFilters} size="xs" variant="subtle">
                    Clear filters
                  </Button>
                ) : null}
              </Group>
              <FilterBar
                filters={filterDefinitions.map((filter) => ({
                  key: filter.key,
                  label: filter.label,
                  options: [{ label: "All", value: "all" }, ...filter.options],
                  value: filters[filter.key] ?? "all",
                }))}
                onFilterChange={(key, value) => {
                  setPage(1);
                  setFilters((current) => ({
                    ...current,
                    [key]: value,
                  }));
                }}
                onSearchChange={
                  getSearchText
                    ? (value) => {
                        setPage(1);
                        setSearchValue(value);
                      }
                    : undefined
                }
                searchLabel={searchLabel}
                searchPlaceholder={searchPlaceholder}
                searchValue={searchValue}
              />
            </Stack>
          </Box>
        ) : null}

        {!filteredRows.length ? (
          <Box p="md">
            {noResultsState ? (
              <>{noResultsState}</>
            ) : (
              <EmptyState
                description="Adjust the current filters or search terms to broaden the result set."
                title={isFiltered ? "No matching records" : "No records yet"}
              />
            )}
          </Box>
        ) : (
          <Table.ScrollContainer minWidth={720}>
            <Table
              aria-label={ariaLabel}
              highlightOnHover
              role="table"
              stickyHeader
              withRowBorders
              withTableBorder={false}
            >
              {caption ? <Table.Caption>{caption}</Table.Caption> : null}
              <Table.Thead>
                <Table.Tr>
                  {columns.map((column) => (
                    <Table.Th
                      aria-sort={getAriaSort(sortState, column)}
                      key={column.key}
                      style={{
                        backgroundColor: semantic.surface_subtle,
                        textAlign: column.align ?? "left",
                        width: column.width,
                      }}
                    >
                      {column.sortable ? (
                        <UnstyledButton
                          aria-label={`Sort by ${String(column.header)}`}
                          onClick={() => {
                            setPage(1);
                            setSortState((current) =>
                              current?.columnKey === column.key
                                ? {
                                    columnKey: column.key,
                                    direction:
                                      current.direction === "asc"
                                        ? "desc"
                                        : "asc",
                                  }
                                : { columnKey: column.key, direction: "asc" },
                            );
                          }}
                          style={{
                            alignItems: "center",
                            color: semantic.text_primary,
                            display: "inline-flex",
                            gap: verifyForGoodTokens.spacing.scale.xs,
                            fontWeight:
                              verifyForGoodTokens.typography.fontWeight.semibold,
                          }}
                        >
                          <span>{column.header}</span>
                          {renderSortIcon(sortState, column.key)}
                        </UnstyledButton>
                      ) : (
                        column.header
                      )}
                    </Table.Th>
                  ))}
                </Table.Tr>
              </Table.Thead>
              <Table.Tbody>
                {pagedRows.map((row, index) => (
                  <Table.Tr
                    key={
                      rowKey
                        ? rowKey(row, pageStartIndex + index)
                        : String(pageStartIndex + index)
                    }
                  >
                    {columns.map((column) => (
                      <Table.Td
                        key={column.key}
                        style={{ textAlign: column.align ?? "left" }}
                      >
                        {renderColumnValue(column, row, index)}
                      </Table.Td>
                    ))}
                  </Table.Tr>
                ))}
              </Table.Tbody>
            </Table>
          </Table.ScrollContainer>
        )}
      </Box>

      {filteredRows.length > 0 && totalPages > 1 ? (
        <Group justify="space-between" wrap="wrap">
          <Text c="dimmed" fz="sm">
            Showing {pageStartIndex + 1}-
            {Math.min(currentPage * pageSize, filteredRows.length)} of{" "}
            {filteredRows.length}
          </Text>
          <Pagination onChange={setPage} total={totalPages} value={currentPage} />
        </Group>
      ) : null}
    </Stack>
  );
}

function renderSortIcon(
  sortState: { columnKey: string; direction: SortDirection } | null,
  columnKey: string,
) {
  if (sortState?.columnKey !== columnKey) {
    return <IconSelector aria-hidden="true" size={16} stroke={1.8} />;
  }

  return sortState.direction === "asc" ? (
    <IconChevronUp aria-hidden="true" size={16} stroke={1.8} />
  ) : (
    <IconChevronDown aria-hidden="true" size={16} stroke={1.8} />
  );
}

function renderColumnValue<T>(
  column: DataTableColumn<T>,
  row: T,
  index: number,
) {
  if (column.render) {
    return column.render(row, index);
  }

  if (column.value) {
    return column.value(row, index);
  }

  return null;
}

function getColumnSortValue<T>(column: DataTableColumn<T>, row: T) {
  const value =
    column.sortValue?.(row) ??
    (typeof column.value === "function" ? column.value(row, 0) : null);

  if (typeof value === "number") {
    return value;
  }

  return String(value ?? "");
}

function getAriaSort<T>(
  sortState: { columnKey: string; direction: SortDirection } | null,
  column: DataTableColumn<T>,
) {
  if (!column.sortable) {
    return "none";
  }

  if (sortState?.columnKey !== column.key) {
    return "none";
  }

  return sortState.direction === "asc" ? "ascending" : "descending";
}
