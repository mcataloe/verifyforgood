import { Stack, TextInput } from "@mantine/core";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { PortalNotice } from "../components/feedback";
import { useEffect, useState } from "react";
import type { PortalBudgetSettingsController } from "./usePortalBudgetSettings";
import { HardStopEnforcementField } from "./HardStopEnforcementField";

interface BudgetConfigurationPanelProps {
  controller: PortalBudgetSettingsController;
  includedPlanLimit?: number | null;
}

export function BudgetConfigurationPanel({
  controller,
  includedPlanLimit = null,
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
    <Stack gap="md">
      <TextInput
        id="monthly-request-cap"
        inputMode="numeric"
        label="Organization request cap"
        min="1"
        onChange={(event) => {
          controller.clearNotice();
          setMonthlyRequestCap(event.target.value);
        }}
        placeholder="Optional"
        type="number"
        value={monthlyRequestCap}
      />
      <PortalHint>{describeCapGuidance(includedPlanLimit)}</PortalHint>
      <HardStopEnforcementField
        allowOverage={allowOverage}
        monthlyRequestCap={parsedMonthlyRequestCap ?? null}
        onChange={(nextHardStopEnabled) => {
          controller.clearNotice();
          setAllowOverage(!nextHardStopEnabled);
        }}
      />

      {validationMessage ? (
        <PortalNotice tone="error">
          <p>{validationMessage}</p>
        </PortalNotice>
      ) : null}

      {controller.error ? (
        <PortalNotice tone="error">
          <p>{controller.error}</p>
        </PortalNotice>
      ) : null}

      {controller.notice ? (
        <PortalNotice tone="warning">
          <p>{controller.notice}</p>
        </PortalNotice>
      ) : null}

      <PortalActionGroup>
        <PortalButton
          disabled={
            controller.isLoading ||
            controller.isSaving ||
            !isDirty ||
            validationMessage !== null
          }
          loading={controller.isSaving}
          onClick={() =>
            void controller.save({
              allowOverage,
              monthlyRequestCap: parsedMonthlyRequestCap ?? null,
            })
          }
          tone="primary"
          type="button"
        >
          {controller.isSaving ? "Saving..." : "Save Budget"}
        </PortalButton>
      </PortalActionGroup>
    </Stack>
  );
}

function describeCapGuidance(includedPlanLimit: number | null): string {
  if (includedPlanLimit !== null) {
    return `Set an optional request cap for this organization. Leave it blank to use the ${includedPlanLimit.toLocaleString()} monthly requests included with your plan.`;
  }

  return "Set an optional request cap for this organization. Leave it blank to use the monthly request allowance included with your plan.";
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
    return "Organization request cap must be a whole number greater than zero.";
  }
  return null;
}

