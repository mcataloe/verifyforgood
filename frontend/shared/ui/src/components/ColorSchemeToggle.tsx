import { Button } from "@mantine/core";
import { useVerifyForGoodColorScheme } from "./VerifyForGoodMantineProvider";

/**
 * Shared light/dark mode toggle that reads from the VerifyForGood color scheme
 * context.
 */
export function ColorSchemeToggle() {
  const { resolvedColorScheme, toggleColorScheme } =
    useVerifyForGoodColorScheme();
  const isDark = resolvedColorScheme === "dark";

  return (
    <Button
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      aria-pressed={isDark}
      onClick={toggleColorScheme}
      variant="light"
    >
      {isDark ? "Light mode" : "Dark mode"}
    </Button>
  );
}
