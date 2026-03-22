import { Group, Stack, Text, type MantineColorScheme } from "@mantine/core";
import { useVerifyForGoodColorScheme } from "./VerifyForGoodMantineProvider";

type ColorSchemeToggleProps = {
  label?: string;
};

/**
 * Shared auto/light/dark mode selector that reads from the VerifyForGood color
 * scheme context.
 */
export function ColorSchemeToggle({
  label = "Theme mode",
}: ColorSchemeToggleProps) {
  const { colorScheme, setColorScheme } = useVerifyForGoodColorScheme();

  return (
    <Stack gap={6}>
      <Text className="vf-theme-mode-control__label" fz="xs" fw={600}>
        {label}
      </Text>
      <Group
        aria-label={label}
        className="vf-theme-mode-control"
        gap={4}
        role="group"
        wrap="nowrap"
      >
        {themeModeOptions.map((option) => (
          <button
            aria-pressed={colorScheme === option.value}
            className="vf-theme-mode-control__button"
            data-active={colorScheme === option.value || undefined}
            key={option.value}
            onClick={() => setColorScheme(option.value)}
            type="button"
          >
            {option.label}
          </button>
        ))}
      </Group>
    </Stack>
  );
}

const themeModeOptions: ReadonlyArray<{
  label: string;
  value: MantineColorScheme;
}> = [
  { label: "Auto", value: "auto" },
  { label: "Light", value: "light" },
  { label: "Dark", value: "dark" },
];
