import {
  ColorSchemeToggle,
  useVerifyForGoodColorScheme,
} from "@charity-status/shared-ui";

/**
 * User-owned appearance preferences for the authenticated portal experience.
 * This stays page-local so shell/footer composition remains context-only.
 */
export function AppearancePreferenceSection() {
  const { colorScheme, resolvedColorScheme } = useVerifyForGoodColorScheme();

  return (
    <section className="portal-settings-preferences" aria-labelledby="appearance-preferences-title">
      <div className="portal-settings-preferences__copy">
        <h3 id="appearance-preferences-title">Appearance</h3>
        <p>
          Choose how VerifyForGood should look for this browser. Auto follows
          the system preference, while Light and Dark stay fixed until changed.
        </p>
      </div>

      <div className="portal-settings-preferences__control">
        <ColorSchemeToggle label="Appearance mode" />
      </div>

      <p className="portal-settings-preferences__note">
        Current selection:{" "}
        <strong>
          {colorScheme === "auto"
            ? `Auto (${resolvedColorScheme})`
            : capitalize(colorScheme)}
        </strong>
      </p>
    </section>
  );
}

function capitalize(value: string) {
  return value.charAt(0).toUpperCase() + value.slice(1);
}
