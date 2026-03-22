import { Box, Group, Stack, Text, Title } from "@mantine/core";
import type { ReactNode } from "react";
import { useVerifyForGoodSemanticColors } from "../../theme/useVerifyForGoodTheme";
import { verifyForGoodTokens } from "../../theme/tokens";

/**
 * Shared expressive hero section for the marketing surface.
 */
export function HeroSection({
  actions,
  description,
  eyebrow = "VerifyForGood",
  sideContent,
  title,
}: {
  actions?: ReactNode;
  description: ReactNode;
  eyebrow?: ReactNode;
  sideContent?: ReactNode;
  title: ReactNode;
}) {
  const { palette, semantic } = useVerifyForGoodSemanticColors();

  return (
    <Box
      style={{
        background: `linear-gradient(135deg, ${palette.primary[50]} 0%, ${semantic.surface} 58%, ${palette.secondary[50]} 100%)`,
        border: `1px solid ${semantic.border}`,
        borderRadius: verifyForGoodTokens.radius.modal,
        overflow: "hidden",
        padding: verifyForGoodTokens.spacing.scale.xl,
      }}
    >
      <Group align="stretch" gap="xl" justify="space-between" wrap="wrap">
        <Stack gap="md" maw="44rem">
          <Text c="dimmed" fw={700} fz="xs" tt="uppercase">
            {eyebrow}
          </Text>
          <Title maw="18ch" order={1}>
            {title}
          </Title>
          <Text c="dimmed" component="div" maw="56ch" size="lg">
            {description}
          </Text>
          {actions ? <Group gap="sm">{actions}</Group> : null}
        </Stack>

        {sideContent ? (
          <Box maw="22rem" miw="18rem" style={{ flex: "1 1 18rem" }}>
            {sideContent}
          </Box>
        ) : null}
      </Group>
    </Box>
  );
}
