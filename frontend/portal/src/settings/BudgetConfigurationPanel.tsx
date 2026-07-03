import { Group, Stack, Text, TextInput } from "@mantine/core";
import {
  PortalActionGroup,
  PortalButton,
  PortalHint,
} from "../components/PortalPrimitives";
import { InfoTooltip } from "../components/InfoTooltip";
import { PortalNotice } from "../components/feedback";
import { useEffect, useState, type ReactNode } from "react";
import type { PortalBudgetSettingsController } from "./usePortalBudgetSettings";
import { HardStopEnforcementField } from "./HardStopEnforcementField";

function LabeledFieldWithTooltip({
  children,
  htmlFor,
  label,
  tooltip,
}: {
  children: ReactNode;
  htmlFor: string;
  label: string;
  tooltip: string;
}) {
  return (
    <Stack gap={4}>
      <Group gap={4}>
        <Text component="label" fw={500} htmlFor={htmlFor} size="sm">
          {label}
        </Text>
        <InfoTooltip label={tooltip} />
      </Group>
      {children}
    </Stack>
  );
}

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
      <LabeledFieldWithTooltip
        htmlFor="monthly-request-cap"
        label="Organization request cap"
        tooltip="An optional monthly request limit for this organization. Leave it blank to use the allowance included with your plan."
      >
        <TextInput
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
      </LabeledFieldWithTooltip>
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
