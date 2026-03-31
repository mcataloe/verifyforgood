import { useEffect, useState } from "react";
import type { PortalBudgetSettingsController } from "./usePortalBudgetSettings";
import { HardStopEnforcementField } from "./HardStopEnforcementField";

interface BudgetConfigurationPanelProps {
  controller: PortalBudgetSettingsController;
}

export function BudgetConfigurationPanel({
  controller,
}: BudgetConfigurationPanelProps) {
  const [allowOverage, setAllowOverage] = useState(
    controller.settings.allowOverage,
  );
  const [monthlyRequestCap, setMonthlyRequestCap] = useState(
    controller.settings.monthlyRequestCap?.toString() ?? "",
  );

  useEffect(() => {
    setAllowOverage(controller.settings.allowOverage);
    setMonthlyRequestCap(
      controller.settings.monthlyRequestCap?.toString() ?? "",
    );
  }, [controller.settings.allowOverage, controller.settings.monthlyRequestCap]);

  const parsedMonthlyRequestCap = parseMonthlyRequestCap(monthlyRequestCap);
  const validationMessage = getValidationMessage(monthlyRequestCap);
  const isDirty =
    allowOverage !== controller.settings.allowOverage ||
    (parsedMonthlyRequestCap ?? null) !== controller.settings.monthlyRequestCap;

  return (
    <div className="portal-budget-form">
      <div className="portal-budget-form__section">
        <label className="portal-form__field" htmlFor="monthly-request-cap">
          <span>Monthly usage cap</span>
          <input
            className="portal-form__input"
            id="monthly-request-cap"
            inputMode="numeric"
            min="1"
            onChange={(event) => {
              controller.clearNotice();
              setMonthlyRequestCap(event.target.value);
            }}
            placeholder="Optional"
            type="number"
            value={monthlyRequestCap}
          />
        </label>
        <p className="portal-budget-form__hint">
          Set the maximum number of requests you want to budget for this month.
          Leave it blank to use the limit included with your plan.
        </p>
      </div>

      <HardStopEnforcementField
        allowOverage={allowOverage}
        monthlyRequestCap={parsedMonthlyRequestCap ?? null}
        onChange={(nextHardStopEnabled) => {
          controller.clearNotice();
          setAllowOverage(!nextHardStopEnabled);
        }}
      />

      {validationMessage ? (
        <p className="portal-feedback portal-feedback--error">
          {validationMessage}
        </p>
      ) : null}

      {controller.error ? (
        <p className="portal-feedback portal-feedback--error">
          {controller.error}
        </p>
      ) : null}

      {controller.notice ? (
        <p className="portal-feedback portal-feedback--warning">
          {controller.notice}
        </p>
      ) : null}

      <div className="portal-form__actions">
        <button
          className="portal-shell__action portal-shell__action--primary"
          disabled={
            controller.isLoading ||
            controller.isSaving ||
            !isDirty ||
            validationMessage !== null
          }
          onClick={() =>
            void controller.save({
              allowOverage,
              monthlyRequestCap: parsedMonthlyRequestCap ?? null,
            })
          }
          type="button"
        >
          {controller.isSaving
            ? "Saving budget controls..."
            : "Save budget controls"}
        </button>
      </div>
    </div>
  );
}

function parseMonthlyRequestCap(value: string): number | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return null;
  }
  return parsed;
}

function getValidationMessage(value: string): string | null {
  const trimmed = value.trim();
  if (!trimmed) {
    return null;
  }
  const parsed = Number.parseInt(trimmed, 10);
  if (!Number.isInteger(parsed) || parsed < 1) {
    return "Monthly usage cap must be a whole number greater than zero.";
  }
  return null;
}

