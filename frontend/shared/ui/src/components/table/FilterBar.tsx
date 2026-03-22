import { Group, NativeSelect, TextInput } from "@mantine/core";
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
        <NativeSelect
          aria-label={filter.label}
          data={filter.options}
          key={filter.key}
          label={filter.label}
          onChange={(event) =>
            onFilterChange?.(filter.key, event.currentTarget.value)
          }
          value={filter.value}
        />
      ))}
    </Group>
  );
}
