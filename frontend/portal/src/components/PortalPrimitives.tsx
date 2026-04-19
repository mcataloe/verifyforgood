import {
  Button,
  Group,
  Paper,
  SimpleGrid,
  Stack,
  Text,
} from "@mantine/core";
import type {
  ComponentPropsWithoutRef,
  PropsWithChildren,
  ReactNode,
} from "react";

export type PortalActionTone = "danger" | "neutral" | "primary" | "secondary";

type PortalButtonProps = PropsWithChildren<{
  disabled?: boolean;
  loading?: boolean;
  onClick?: ComponentPropsWithoutRef<"button">["onClick"];
  tone?: PortalActionTone;
  type?: "button" | "reset" | "submit";
}>;

type PortalAnchorButtonProps = PropsWithChildren<{
  href: string;
  rel?: string;
  target?: string;
  tone?: PortalActionTone;
}>;

export type PortalDetailListItem = {
  key: string;
  label: ReactNode;
  value: ReactNode;
};

export function PortalButton({
  tone = "neutral",
  ...props
}: PortalButtonProps) {
  const presentation = resolveButtonPresentation(tone);

  return (
    <Button
      color={presentation.color}
      variant={presentation.variant}
      {...props}
    />
  );
}

export function PortalAnchorButton({
  children,
  href,
  tone = "neutral",
  ...props
}: PortalAnchorButtonProps) {
  const presentation = resolveButtonPresentation(tone);

  return (
    <Button
      component="a"
      href={href}
      color={presentation.color}
      variant={presentation.variant}
      {...props}
    >
      {children}
    </Button>
  );
}

export function PortalActionGroup({
  children,
}: PropsWithChildren) {
  return (
    <Group align="center" gap="sm" wrap="wrap">
      {children}
    </Group>
  );
}

export function PortalHint({ children }: PropsWithChildren) {
  return (
    <Text c="dimmed" fz="sm" lh={1.6}>
      {children}
    </Text>
  );
}

export function PortalFeedbackText({
  children,
  tone = "muted",
}: PropsWithChildren<{ tone?: "danger" | "muted" }>) {
  return (
    <Text c={tone === "danger" ? "red" : "dimmed"} fz="sm" lh={1.6}>
      {children}
    </Text>
  );
}

export function PortalDetailList({
  items,
  columns = 2,
}: {
  columns?: number;
  items: PortalDetailListItem[];
}) {
  return (
    <SimpleGrid cols={{ base: 1, md: columns }} spacing="sm">
      {items.map((item) => (
        <Paper key={item.key} p="md" radius="md" withBorder>
          <Stack gap={2}>
            <Text c="dimmed" fw={700} fz="xs" tt="uppercase">
              {item.label}
            </Text>
            <Text fw={500}>{item.value}</Text>
          </Stack>
        </Paper>
      ))}
    </SimpleGrid>
  );
}

export function PortalMetricGrid({ children }: PropsWithChildren) {
  return (
    <SimpleGrid cols={{ base: 1, sm: 2, lg: 3 }} spacing="sm">
      {children}
    </SimpleGrid>
  );
}

export function PortalMetricCard({
  label,
  value,
}: {
  label: ReactNode;
  value: ReactNode;
}) {
  return (
    <Paper p="md" radius="md" withBorder>
      <Stack gap={2}>
        <Text c="dimmed" fz="sm">
          {label}
        </Text>
        <Text fw={700} size="lg">
          {value}
        </Text>
      </Stack>
    </Paper>
  );
}

function resolveButtonPresentation(tone: PortalActionTone) {
  switch (tone) {
    case "primary":
      return {
        color: "dark",
        variant: "filled" as const,
      };
    case "secondary":
      return {
        color: "gray",
        variant: "default" as const,
      };
    case "danger":
      return {
        color: "red",
        variant: "filled" as const,
      };
    case "neutral":
    default:
      return {
        color: "gray",
        variant: "light" as const,
      };
  }
}
