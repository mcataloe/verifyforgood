import "@mantine/core/styles.css";
import "../styles.css";

import {
  MantineProvider,
  localStorageColorSchemeManager,
  useComputedColorScheme,
  useMantineColorScheme,
  type MantineColorScheme,
} from "@mantine/core";
import {
  createContext,
  useContext,
  useMemo,
  type PropsWithChildren,
} from "react";
import { verifyForGoodMantineTheme } from "../theme/mantineTheme";
import type { VerifyForGoodThemeMode } from "../theme/tokens";
import { ThemeRoot } from "./ThemeRoot";

type VerifyForGoodMantineProviderProps = PropsWithChildren<{
  className?: string;
  defaultColorScheme?: MantineColorScheme;
}>;

type VerifyForGoodColorSchemeValue = {
  colorScheme: MantineColorScheme;
  resolvedColorScheme: VerifyForGoodThemeMode;
  setColorScheme: (value: MantineColorScheme) => void;
  toggleColorScheme: () => void;
  clearColorScheme: () => void;
};

const VERIFY_FOR_GOOD_COLOR_SCHEME_KEY = "verifyforgood-color-scheme";

const verifyForGoodColorSchemeManager = localStorageColorSchemeManager({
  key: VERIFY_FOR_GOOD_COLOR_SCHEME_KEY,
});

const VerifyForGoodColorSchemeContext =
  createContext<VerifyForGoodColorSchemeValue | null>(null);

/**
 * Example Mantine provider wrapper for VerifyForGood applications.
 *
 * It keeps the shared CSS theme root and Mantine color scheme state aligned so
 * both Mantine components and existing shared-ui primitives read from the same
 * light/dark mode selection.
 */
export function VerifyForGoodMantineProvider({
  children,
  className,
  defaultColorScheme = "light",
}: VerifyForGoodMantineProviderProps) {
  return (
    <MantineProvider
      colorSchemeManager={verifyForGoodColorSchemeManager}
      defaultColorScheme={defaultColorScheme}
      theme={verifyForGoodMantineTheme}
    >
      <VerifyForGoodMantineBridge className={className}>
        {children}
      </VerifyForGoodMantineBridge>
    </MantineProvider>
  );
}

export function useVerifyForGoodColorScheme() {
  const context = useContext(VerifyForGoodColorSchemeContext);

  if (!context) {
    throw new Error(
      "useVerifyForGoodColorScheme must be used within VerifyForGoodMantineProvider",
    );
  }

  return context;
}

function VerifyForGoodMantineBridge({
  children,
  className,
}: PropsWithChildren<{ className?: string }>) {
  const { clearColorScheme, colorScheme, setColorScheme } =
    useMantineColorScheme();
  const resolvedColorScheme = useComputedColorScheme(
    "light",
  ) as VerifyForGoodThemeMode;

  const value = useMemo<VerifyForGoodColorSchemeValue>(
    () => ({
      clearColorScheme,
      colorScheme,
      resolvedColorScheme,
      setColorScheme,
      toggleColorScheme: () =>
        setColorScheme(resolvedColorScheme === "dark" ? "light" : "dark"),
    }),
    [clearColorScheme, colorScheme, resolvedColorScheme, setColorScheme],
  );

  return (
    <VerifyForGoodColorSchemeContext.Provider value={value}>
      <ThemeRoot
        className={className}
        tone={resolvedColorScheme === "dark" ? "inverse" : "default"}
      >
        {children}
      </ThemeRoot>
    </VerifyForGoodColorSchemeContext.Provider>
  );
}
