import { ActionIcon, Tooltip } from "@mantine/core";
import { IconInfoCircle } from "@tabler/icons-react";

interface InfoTooltipProps {
  label: string;
}

export function InfoTooltip({ label }: InfoTooltipProps) {
  return (
    <Tooltip label={label} multiline withArrow withinPortal>
      <ActionIcon
        aria-label="More information"
        color="gray"
        radius="xl"
        size="sm"
        type="button"
        variant="subtle"
      >
        <IconInfoCircle aria-hidden="true" size={16} />
      </ActionIcon>
    </Tooltip>
  );
}
