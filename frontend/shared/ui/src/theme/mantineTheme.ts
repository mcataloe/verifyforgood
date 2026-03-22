import {
  Badge,
  Button,
  Card,
  createTheme,
  Modal,
  Table,
  TextInput,
  type MantineColorsTuple,
} from "@mantine/core";
import { verifyForGoodTokens } from "./tokens";

type TokenPalette = Record<
  50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900,
  string
>;

const spacing = verifyForGoodTokens.spacing.scale;
const radius = verifyForGoodTokens.radius;
const typography = verifyForGoodTokens.typography;

function toMantineColorsTuple(palette: TokenPalette): MantineColorsTuple {
  return [
    palette[50],
    palette[100],
    palette[200],
    palette[300],
    palette[400],
    palette[500],
    palette[600],
    palette[700],
    palette[800],
    palette[900],
  ];
}

function toMantineHeadingStyle(
  heading: (typeof verifyForGoodTokens.typography.headings)[keyof typeof verifyForGoodTokens.typography.headings],
) {
  return {
    fontSize: heading.fontSize,
    fontWeight: String(heading.fontWeight),
    lineHeight: String(heading.lineHeight),
  };
}

/**
 * Mantine theme bridge for VerifyForGood.
 *
 * The Mantine theme is derived entirely from the shared token module so Mantine
 * stays an implementation detail instead of becoming the token source of truth.
 */
export const verifyForGoodMantineTheme = createTheme({
  autoContrast: true,
  primaryColor: "primary",
  primaryShade: { light: 6, dark: 4 },
  colors: {
    primary: toMantineColorsTuple(verifyForGoodTokens.color.palette.primary),
    secondary: toMantineColorsTuple(verifyForGoodTokens.color.palette.secondary),
    success: toMantineColorsTuple(verifyForGoodTokens.color.palette.success),
    warning: toMantineColorsTuple(verifyForGoodTokens.color.palette.warning),
    danger: toMantineColorsTuple(verifyForGoodTokens.color.palette.danger),
    gray: toMantineColorsTuple(verifyForGoodTokens.color.palette.neutral),
  },
  fontFamily: typography.fontFamily.sans,
  fontFamilyMonospace: typography.fontFamily.mono,
  fontSizes: {
    xs: typography.fontSize.xs,
    sm: typography.fontSize.sm,
    md: typography.fontSize.md,
    lg: typography.fontSize.lg,
    xl: typography.fontSize.xl,
  },
  lineHeights: {
    xs: String(typography.lineHeight.tight),
    sm: String(typography.lineHeight.snug),
    md: String(typography.lineHeight.normal),
    lg: String(typography.lineHeight.relaxed),
    xl: String(typography.lineHeight.relaxed),
  },
  headings: {
    fontFamily: typography.fontFamily.sans,
    fontWeight: String(typography.fontWeight.bold),
    textWrap: "balance",
    sizes: {
      h1: toMantineHeadingStyle(typography.headings.h1),
      h2: toMantineHeadingStyle(typography.headings.h2),
      h3: toMantineHeadingStyle(typography.headings.h3),
      h4: toMantineHeadingStyle(typography.headings.h4),
      h5: toMantineHeadingStyle(typography.headings.h5),
      h6: toMantineHeadingStyle(typography.headings.h6),
    },
  },
  spacing: {
    xs: spacing.xs,
    sm: spacing.sm,
    md: spacing.md,
    lg: spacing.lg,
    xl: spacing.xl,
  },
  radius: {
    xs: radius.input,
    sm: radius.button,
    md: radius.card,
    lg: radius.modal,
    xl: radius.modal,
  },
  defaultRadius: "sm",
  shadows: {
    xs: verifyForGoodTokens.shadow.subtle,
    sm: verifyForGoodTokens.shadow.card,
    md: verifyForGoodTokens.shadow.modal,
    xl: verifyForGoodTokens.shadow.overlay,
  },
  other: {
    verifyForGood: verifyForGoodTokens,
  },
  components: {
    Button: Button.extend({
      defaultProps: {
        color: "primary",
        radius: "sm",
        size: "md",
      },
      styles: {
        root: {
          fontWeight: typography.fontWeight.semibold,
          paddingInline: spacing.md,
        },
      },
    }),
    Card: Card.extend({
      defaultProps: {
        padding: "lg",
        radius: "md",
        shadow: "sm",
        withBorder: true,
      },
    }),
    TextInput: TextInput.extend({
      defaultProps: {
        radius: "xs",
        size: "md",
      },
      styles: {
        input: {
          paddingInline: spacing.sm,
        },
      },
    }),
    Badge: Badge.extend({
      defaultProps: {
        color: "secondary",
        radius: "xl",
        size: "lg",
        variant: "light",
      },
      styles: {
        root: {
          fontWeight: typography.fontWeight.medium,
          paddingInline: spacing.sm,
        },
      },
    }),
    Table: Table.extend({
      defaultProps: {
        highlightOnHover: true,
        horizontalSpacing: "md",
        verticalSpacing: "sm",
        withRowBorders: true,
        withTableBorder: true,
      },
      styles: {
        th: {
          paddingBlock: spacing.sm,
        },
        td: {
          paddingBlock: spacing.sm,
        },
      },
    }),
    Modal: Modal.extend({
      defaultProps: {
        centered: true,
        padding: "lg",
        radius: "lg",
        shadow: "md",
      },
    }),
  },
});
