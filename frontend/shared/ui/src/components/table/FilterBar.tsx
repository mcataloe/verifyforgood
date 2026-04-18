import { Group, Select, TextInput } from "@mantine/core";
import { IconSearch } from "@tabler/icons-react";
import type { ChangeEvent } from "react";

export type FilterBarOption = {
  label: string;
  value: string;
};

export type FilterBarFilter = {
  key: string;
  label: string;
  options: FilterBarOption[];
  value: string;
};

type FilterBarProps = {
  filters?: FilterBarFilter[];
  onFilterChange?: (key: string, value: string) => void;
  onSearchChange?: (value: string) => void;
  searchLabel?: string;
  searchPlaceholder?: string;
  searchValue?: string;
};

/**
 * Compact filter surface for shared table experiences.
 */
export function FilterBar({
  filters = [],
  onFilterChange,
  onSearchChange,
  searchLabel = "Search records",
  searchPlaceholder = "Search",
  searchValue = "",
}: FilterBarProps) {
  if (!onSearchChange && !filters.length) {
    return null;
  }

  return (
    <Group align="end" gap="sm" wrap="wrap">
      {onSearchChange ? (
        <TextInput
          aria-label={searchLabel}
          leftSection={<IconSearch aria-hidden="true" size={16} stroke={1.8} />}
          label={searchLabel}
          miw={280}
          onChange={(event: ChangeEvent<HTMLInputElement>) =>
            onSearchChange(event.currentTarget.value)
          }
          placeholder={searchPlaceholder}
          value={searchValue}
        />
      ) : null}

      {filters.map((filter) => (
        <Select
          aria-label={filter.label}
          data={filter.options}
          key={filter.key}
          label={filter.label}
          onChange={(event) =>
            onFilterChange?.(filter.key, event ?? "all")
          }
          value={filter.value}
        />
      ))}
    </Group>
  );
}
