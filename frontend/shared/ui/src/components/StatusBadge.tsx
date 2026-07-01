import { Badge } from "@mantine/core";
import { useComputedColorScheme } from "@mantine/core";
import {
  verifyForGoodTokens,
  type VerifyForGoodThemeMode,
} from "../theme/tokens";

export type StatusBadgeStatus =
  | "complete"
  | "conflicting"
  | "flagged"
  | "inactive"
  | "incomplete"
  | "not_recorded"
  | "pending"
  | "review_required"
  | "source_unavailable"
  | "stale"
  | "verified";

type StatusBadgeProps = {
  label?: string;
  status: StatusBadgeStatus;
};

const STATUS_BADGE_LABELS: Record<StatusBadgeStatus, string> = {
  complete: "Evidence complete",
  conflicting: "Conflicting evidence",
  flagged: "Review required",
  inactive: "Inactive",
  incomplete: "Evidence incomplete",
  not_recorded: "Not recorded",
  pending: "Pending review",
  review_required: "Review required",
  source_unavailable: "Source unavailable",
  stale: "Stale evidence",
  verified: "Evidence complete",
};

/**
 * Small semantic state badge for platform workflows.
 *
 * Example:
 * ```tsx
 * <StatusBadge status="complete" />
 * <StatusBadge status="flagged" label="Needs review" />
 * ```
 */
export function StatusBadge({ label, status }: StatusBadgeProps) {
  const colorScheme = useComputedColorScheme("light") as VerifyForGoodThemeMode;
  const palette =
    status === "complete" || status === "verified"
      ? verifyForGoodTokens.color.palette.success
      : status === "pending" ||
          status === "incomplete" ||
          status === "stale" ||
          status === "not_recorded"
        ? verifyForGoodTokens.color.palette.warning
        : status === "flagged" ||
            status === "review_required" ||
            status === "conflicting" ||
            status === "source_unavailable"
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
      aria-label={`Status: ${label ?? STATUS_BADGE_LABELS[status]}`}
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
