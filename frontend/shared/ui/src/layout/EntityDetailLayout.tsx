import {
  Badge,
  Box,
  Button,
  Card,
  Group,
  SimpleGrid,
  Stack,
  Tabs,
  Text,
  Title,
} from "@mantine/core";
import type { ReactNode } from "react";
import { PageHeader } from "../components/PageHeader";
import { StatusBadge, type StatusBadgeStatus } from "../components/StatusBadge";
import { useVerifyForGoodSemanticColors } from "../theme/useVerifyForGoodTheme";
import { verifyForGoodTokens } from "../theme/tokens";

export type EntityDetailSummaryItem = {
  detail?: ReactNode;
  key: string;
  label: string;
  value: ReactNode;
};
export type EntityDetailTab = {
  content: ReactNode;
  key: string;
  label: string;
};
type EntityDetailLayoutProps = {
  actions?: ReactNode;
  activeTabKey?: string;
  description?: ReactNode;
  ein: string;
  identifierLabel?: string;
  name: string;
  primaryActionLabel?: string;
  onPrimaryAction?: () => void;
  onTabChange?: (key: string) => void;
  status: StatusBadgeStatus;
  summaryItems: EntityDetailSummaryItem[];
  tabs: EntityDetailTab[];
};

export function EntityDetailLayout({
  actions,
  activeTabKey,
  description,
  ein,
  identifierLabel = "EIN",
  name,
  onPrimaryAction,
  onTabChange,
  primaryActionLabel = "Request refresh",
  status,
  summaryItems,
  tabs,
}: EntityDetailLayoutProps) {
  const { semantic } = useVerifyForGoodSemanticColors();
  const tabState = activeTabKey
    ? { value: activeTabKey }
    : { defaultValue: tabs[0]?.key };

  return (
    <Stack gap="lg">
      <PageHeader
        actions={
          <Group gap="sm">
            {actions}
            <Button onClick={onPrimaryAction} variant="light">
              {primaryActionLabel}
            </Button>
          </Group>
        }
        description={description}
        eyebrow="Entity review"
        title={
          <Stack gap="xs">
            <Group gap="sm" wrap="wrap">
              <Title order={2}>{name}</Title>
              <StatusBadge status={status} />
            </Group>
            <Group gap="sm" wrap="wrap">
              <Badge color="gray" variant="light">
                {identifierLabel}: {ein}
              </Badge>
            </Group>
          </Stack>
        }
      />

      <SimpleGrid cols={{ base: 1, md: 2, xl: 4 }} spacing="md">
        {summaryItems.map((item) => (
          <Card key={item.key} padding="lg" radius="md" shadow="sm" withBorder>
            <Stack gap="xs">
              <Text c="dimmed" fw={600} fz="xs" tt="uppercase">
                {item.label}
              </Text>
              <Text fw={700}>{item.value}</Text>
              {item.detail ? (
                <Text c="dimmed" component="div" fz="sm">
                  {item.detail}
                </Text>
              ) : null}
            </Stack>
          </Card>
        ))}
      </SimpleGrid>

      <Tabs
        color="primary"
        keepMounted={false}
        onChange={(value) => {
          if (value) onTabChange?.(value);
        }}
        variant="outline"
        {...tabState}
      >
        <Tabs.List aria-label="Entity detail sections">
          {tabs.map((tab) => (
            <Tabs.Tab key={tab.key} value={tab.key}>
              {tab.label}
            </Tabs.Tab>
          ))}
        </Tabs.List>
        {tabs.map((tab) => (
          <Tabs.Panel key={tab.key} pt="md" value={tab.key}>
            <Box
              style={{
                backgroundColor: semantic.surface,
                border: `1px solid ${semantic.border}`,
                borderRadius: verifyForGoodTokens.radius.card,
                padding: verifyForGoodTokens.spacing.scale.lg,
              }}
            >
              {tab.content}
            </Box>
          </Tabs.Panel>
        ))}
      </Tabs>
    </Stack>
  );
}
