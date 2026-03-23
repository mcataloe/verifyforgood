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
    <div className="portal-budget-form__section">
      <label className="portal-budget-toggle">
        <input
          checked={hardStopEnabled}
          onChange={(event) => {
            onChange(event.target.checked);
          }}
          type="checkbox"
        />
        <span>Enable hard-stop enforcement</span>
      </label>
      <p className="portal-budget-form__hint">
        {describeBudgetConsequence({
          allowOverage,
          monthlyRequestCap,
        })}
      </p>
    </div>
  );
}

export function describeBudgetConsequence(input: {
  allowOverage: boolean;
  monthlyRequestCap: number | null;
}): string {
  if (!input.allowOverage && input.monthlyRequestCap !== null) {
    return `Requests stop once usage reaches ${input.monthlyRequestCap.toLocaleString()} this month.`;
  }

  if (!input.allowOverage) {
    return "Requests stop at the included plan limit when the monthly allowance is exhausted.";
  }

  if (input.monthlyRequestCap !== null) {
    return `Requests can continue beyond ${input.monthlyRequestCap.toLocaleString()} if needed, so this cap acts as a visible budget target while overage remains enabled.`;
  }

  return "Requests can continue beyond included usage and may incur overage under the active plan.";
}
