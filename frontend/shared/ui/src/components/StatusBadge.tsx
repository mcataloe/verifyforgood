import { Badge } from "@mantine/core";
import { useComputedColorScheme } from "@mantine/core";
import { verifyForGoodTokens, type VerifyForGoodThemeMode } from "../theme/tokens";

export type StatusBadgeStatus = "verified" | "pending" | "flagged" | "inactive";

type StatusBadgeProps = {
  label?: string;
  status: StatusBadgeStatus;
};

const STATUS_BADGE_LABELS: Record<StatusBadgeStatus, string> = {
  verified: "Verified",
  pending: "Pending",
  flagged: "Flagged",
  inactive: "Inactive",
};

/**
 * Small semantic state badge for platform workflows.
 *
 * Example:
 * ```tsx
 * <StatusBadge status="verified" />
 * <StatusBadge status="flagged" label="Needs review" />
 * ```
 */
export function StatusBadge({ label, status }: StatusBadgeProps) {
  const colorScheme = useComputedColorScheme("light") as VerifyForGoodThemeMode;
  const palette =
    status === "verified"
      ? verifyForGoodTokens.color.palette.success
      : status === "pending"
        ? verifyForGoodTokens.color.palette.warning
        : status === "flagged"
          ? verifyForGoodTokens.color.palette.danger
          : verifyForGoodTokens.color.palette.neutral;

  const styles =
    colorScheme === "dark"
      ? {
          backgroundColor: palette[900],
          borderColor: palette[700],
          color: palette[100],
        }
      : {
          backgroundColor: palette[100],
          borderColor: palette[200],
          color: palette[700],
        };

  return (
    <Badge
      styles={{
        root: {
          ...styles,
          borderWidth: 1,
          borderStyle: "solid",
          paddingInline: verifyForGoodTokens.spacing.scale.sm,
        },
      }}
      variant="filled"
    >
      {label ?? STATUS_BADGE_LABELS[status]}
    </Badge>
  );
}
