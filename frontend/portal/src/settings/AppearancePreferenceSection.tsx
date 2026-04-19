import {
  ColorSchemeToggle,
  useVerifyForGoodColorScheme,
} from "@charity-status/shared-ui";
import { Paper, Stack, Text, Title } from "@mantine/core";

/**
 * User-owned appearance preferences for the authenticated portal experience.
 * This stays page-local so shell/footer composition remains context-only.
 */
export function AppearancePreferenceSection({
  showTitle = true,
}: {
  showTitle?: boolean;
} = {}) {
  const { colorScheme, resolvedColorScheme } = useVerifyForGoodColorScheme();

  return (
    <Paper
      aria-labelledby={showTitle ? "appearance-preferences-title" : undefined}
      p="lg"
      radius="lg"
      withBorder
    >
      <Stack gap="md">
        {showTitle ? (
          <Title id="appearance-preferences-title" order={3}>
            Appearance
          </Title>
        ) : null}
        <Text c="dimmed" size="sm">
          Choose how VerifyForGood should look for this browser. Auto follows
          the system preference, while Light and Dark stay fixed until changed.
        </Text>

        <ColorSchemeToggle label="Appearance mode" />

        <Text c="dimmed" size="sm">
        Current selection:{" "}
        <strong>
          {colorScheme === "auto"
            ? `Auto (${resolvedColorScheme})`
            : capitalize(colorScheme)}
        </strong>
        </Text>
      </Stack>
    </Paper>
  );
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
