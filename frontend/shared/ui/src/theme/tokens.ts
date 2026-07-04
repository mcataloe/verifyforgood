/**
 * VerifyForGood design tokens define the cross-surface visual foundation for
 * calm, trustworthy, compliance-focused interfaces.
 *
 * Example usage:
 * ```ts
 * import { verifyForGoodTokens } from "@charity-status/shared-ui";
 *
 * const mode = "light";
 * const colors = verifyForGoodTokens.color.semantic[mode];
 *
 * const panelStyle = {
 *   backgroundColor: colors.surface,
 *   color: colors.text_primary,
 *   border: `1px solid ${colors.border}`,
 *   borderRadius: verifyForGoodTokens.radius.card,
 *   boxShadow: verifyForGoodTokens.shadow.card,
 *   padding: verifyForGoodTokens.spacing.scale.lg,
 *   fontFamily: verifyForGoodTokens.typography.fontFamily.sans,
 * };
 * ```
 */

export const verifyForGoodThemeModes = ["light", "dark"] as const;

export type VerifyForGoodThemeMode = (typeof verifyForGoodThemeModes)[number];

export const verifyForGoodTokens = {
  color: {
    palette: {
      primary: {
        50: "#eff6ff",
        100: "#dbeafe",
        200: "#bfd8fb",
        300: "#93bff7",
        400: "#5f9bec",
        500: "#3277d6",
        600: "#215dc2",
        700: "#1d4c9d",
        800: "#1d427f",
        900: "#1d3869",
        950: "#152544",
      },
      secondary: {
        50: "#eefaf9",
        100: "#d5f2f0",
        200: "#afe5e2",
        300: "#79d0ce",
        400: "#43b4b6",
        500: "#24969d",
        600: "#197a83",
        700: "#17626a",
        800: "#174f56",
        900: "#184249",
        950: "#0a272d",
      },
      success: {
        50: "#effbf3",
        100: "#d9f6e1",
        200: "#b6ebc6",
        300: "#84d99d",
        400: "#4fbe70",
        500: "#2f9d54",
        600: "#227d43",
        700: "#1d6338",
        800: "#1b4f31",
        900: "#173f29",
        950: "#0b2417",
      },
      warning: {
        50: "#fffaeb",
        100: "#fff1c6",
        200: "#ffe288",
        300: "#ffcc4a",
        400: "#f4b022",
        500: "#d99214",
        600: "#b56d10",
        700: "#925011",
        800: "#784014",
        900: "#643614",
        950: "#3a1b09",
      },
      danger: {
        50: "#fff2f1",
        100: "#ffe2de",
        200: "#ffc9c2",
        300: "#ffa499",
        400: "#fb7363",
        500: "#ea4f3d",
        600: "#c93c2d",
        700: "#a83025",
        800: "#8b2a22",
        900: "#742821",
        950: "#3e110d",
      },
      neutral: {
        0: "#ffffff",
        50: "#f8fafc",
        100: "#f1f5f9",
        200: "#e2e8f0",
        300: "#cbd5e1",
        400: "#94a3b8",
        500: "#64748b",
        600: "#475569",
        700: "#334155",
        800: "#1e293b",
        900: "#0f172a",
        950: "#020617",
      },
    },
    semantic: {
      light: {
        primary: "#215dc2",
        secondary: "#197a83",
        success: "#227d43",
        warning: "#b56d10",
        danger: "#c93c2d",
        background: "#f8fafc",
        surface: "#ffffff",
        surface_subtle: "#f1f5f9",
        border: "#d7dee8",
        text_primary: "#10233c",
        text_secondary: "#526173",
      },
      dark: {
        primary: "#e4e4e7",
        secondary: "#d4d4d8",
        success: "#4fbe70",
        warning: "#f4b022",
        danger: "#fb7363",
        background: "#0a0a0b",
        surface: "#17171a",
        surface_subtle: "#212124",
        border: "#3a3a3f",
        text_primary: "#f4f4f5",
        text_secondary: "#a1a1aa",
      },
    },
  },
  typography: {
    fontFamily: {
      sans: 'Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, "Helvetica Neue", sans-serif',
      mono: '"SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace',
    },
    fontSize: {
      xs: "12px",
      sm: "14px",
      md: "16px",
      lg: "18px",
      xl: "20px",
      "2xl": "24px",
      "3xl": "30px",
      "4xl": "36px",
      "5xl": "48px",
    },
    lineHeight: {
      tight: 1.1,
      snug: 1.25,
      normal: 1.5,
      relaxed: 1.7,
    },
    fontWeight: {
      regular: 400,
      medium: 500,
      semibold: 600,
      bold: 700,
    },
    letterSpacing: {
      tight: "-0.03em",
      normal: "0",
      wide: "0.02em",
      caps: "0.08em",
    },
    headings: {
      h1: { fontSize: "48px", lineHeight: 1.05, fontWeight: 700, letterSpacing: "-0.03em" },
      h2: { fontSize: "36px", lineHeight: 1.1, fontWeight: 700, letterSpacing: "-0.02em" },
      h3: { fontSize: "30px", lineHeight: 1.15, fontWeight: 600, letterSpacing: "-0.02em" },
      h4: { fontSize: "24px", lineHeight: 1.2, fontWeight: 600, letterSpacing: "-0.01em" },
      h5: { fontSize: "20px", lineHeight: 1.25, fontWeight: 600, letterSpacing: "-0.01em" },
      h6: { fontSize: "18px", lineHeight: 1.3, fontWeight: 600, letterSpacing: "0" },
    },
  },
  spacing: {
    baseUnit: 8,
    scale: {
      xs: "8px",
      sm: "16px",
      md: "24px",
      lg: "32px",
      xl: "40px",
      "2xl": "48px",
    },
  },
  radius: {
    button: "10px",
    card: "16px",
    input: "10px",
    modal: "20px",
  },
  shadow: {
    subtle: "0 1px 2px rgba(15, 23, 42, 0.08)",
    card: "0 12px 32px rgba(15, 23, 42, 0.12)",
    modal: "0 24px 64px rgba(2, 6, 23, 0.18)",
    overlay: "0 0 0 1px rgba(148, 163, 184, 0.18), 0 32px 80px rgba(2, 6, 23, 0.28)",
  },
} as const;

export type VerifyForGoodTokens = typeof verifyForGoodTokens;
