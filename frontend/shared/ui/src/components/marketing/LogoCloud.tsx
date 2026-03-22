import { Group, Text } from "@mantine/core";

/**
 * Lightweight trust band for marketing pages without introducing heavy brand
 * assets.
 */
export function LogoCloud({ items }: { items: string[] }) {
  return (
    <Group
      aria-label="Example customer and program categories"
      gap="sm"
      role="list"
      wrap="wrap"
    >
      {items.map((item) => (
        <Text
          component="span"
          fw={600}
          key={item}
          role="listitem"
          style={{
            border: "1px solid var(--mantine-color-gray-3)",
            borderRadius: "999px",
            padding: "0.55rem 0.85rem",
          }}
        >
          {item}
        </Text>
      ))}
    </Group>
  );
}
