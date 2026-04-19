import { Checkbox, Paper, Stack } from "@mantine/core";
import { PortalHint } from "../components/PortalPrimitives";

interface HardStopEnforcementFieldProps {
  allowOverage: boolean;
  monthlyRequestCap: number | null;
  onChange: (nextHardStopEnabled: boolean) => void;
}

export function HardStopEnforcementField({
  allowOverage,
  monthlyRequestCap,
  onChange,
}: HardStopEnforcementFieldProps) {
  const hardStopEnabled = !allowOverage;

  return (
    <Paper p="md" radius="md" withBorder>
      <Stack gap="sm">
        <Checkbox
          checked={hardStopEnabled}
          label="Enable hard-stop enforcement"
          onChange={(event) => {
            onChange(event.target.checked);
          }}
        />
        <PortalHint>
        {describeBudgetConsequence({
          allowOverage,
          monthlyRequestCap,
        })}
        </PortalHint>
      </Stack>
    </Paper>
  );
}

export function describeBudgetConsequence(input: {
  allowOverage: boolean;
  monthlyRequestCap: number | null;
}): string {
  if (!input.allowOverage && input.monthlyRequestCap !== null) {
    return `Requests stop once organization usage reaches ${input.monthlyRequestCap.toLocaleString()} requests in the current period.`;
  }

  if (!input.allowOverage) {
    return "Requests stop at the included plan allowance when the monthly limit is exhausted.";
  }

  if (input.monthlyRequestCap !== null) {
    return `Requests can continue beyond ${input.monthlyRequestCap.toLocaleString()} if needed, so this cap acts as a budget target while overage remains enabled.`;
  }

  return "Requests can continue beyond included usage and may incur overage under the active plan.";
}
