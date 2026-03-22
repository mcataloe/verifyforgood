import { Box, Table, Text } from "@mantine/core";
import type { ReactNode } from "react";
import { verifyForGoodTokens } from "../theme/tokens";

export type DataTableColumn<T> = {
  align?: "left" | "center" | "right";
  header: ReactNode;
  key: string;
  render: (row: T, index: number) => ReactNode;
  width?: string;
};

type DataTableProps<T> = {
  caption?: ReactNode;
  columns: DataTableColumn<T>[];
  emptyState?: ReactNode;
  rowKey?: (row: T, index: number) => string;
  rows: T[];
};

/**
 * Lightweight data table wrapper around Mantine `Table`.
 *
 * Example:
 * ```tsx
 * <DataTable
 *   columns={[
 *     { key: "name", header: "Organization", render: (row) => row.name },
 *     { key: "status", header: "Status", render: (row) => <StatusBadge status={row.status} /> },
 *   ]}
 *   rows={records}
 * />
 * ```
 */
export function DataTable<T>({
  caption,
  columns,
  emptyState = "No records available.",
  rowKey,
  rows,
}: DataTableProps<T>) {
  if (!rows.length) {
    return (
      <Box
        px="md"
        py="lg"
        style={{
          border: "1px dashed var(--mantine-color-gray-4)",
          borderRadius: verifyForGoodTokens.radius.card,
        }}
      >
        <Text c="dimmed" fz="sm">
          {emptyState}
        </Text>
      </Box>
    );
  }

  return (
    <Box
      style={{
        borderRadius: verifyForGoodTokens.radius.card,
        overflow: "hidden",
      }}
    >
      <Table.ScrollContainer minWidth={720}>
        <Table>
          {caption ? <Table.Caption>{caption}</Table.Caption> : null}
          <Table.Thead>
            <Table.Tr>
              {columns.map((column) => (
                <Table.Th
                  key={column.key}
                  style={{
                    textAlign: column.align ?? "left",
                    width: column.width,
                  }}
                >
                  {column.header}
                </Table.Th>
              ))}
            </Table.Tr>
          </Table.Thead>
          <Table.Tbody>
            {rows.map((row, index) => (
              <Table.Tr key={rowKey ? rowKey(row, index) : String(index)}>
                {columns.map((column) => (
                  <Table.Td
                    key={column.key}
                    style={{ textAlign: column.align ?? "left" }}
                  >
                    {column.render(row, index)}
                  </Table.Td>
                ))}
              </Table.Tr>
            ))}
          </Table.Tbody>
        </Table>
      </Table.ScrollContainer>
    </Box>
  );
}
