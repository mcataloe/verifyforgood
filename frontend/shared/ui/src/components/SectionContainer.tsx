import { Box, Stack, type MantineSpacing } from "@mantine/core";
import type { PropsWithChildren, ReactNode } from "react";
import { verifyForGoodTokens } from "../theme/tokens";
import { PageHeader } from "./PageHeader";

type SectionContainerProps = PropsWithChildren<{
  actions?: ReactNode;
  description?: ReactNode;
  eyebrow?: ReactNode;
  gap?: MantineSpacing;
  title?: ReactNode;
}>;

/**
 * Shared section wrapper that provides consistent vertical rhythm and optional
 * section heading metadata.
 *
 * Example:
 * ```tsx
 * <SectionContainer
 *   title="Recent verifications"
 *   description="Latest nonprofit checks across the current workspace."
 * >
 *   <DataTable columns={columns} rows={rows} />
 * </SectionContainer>
 * ```
 */
export function SectionContainer({
  actions,
  children,
  description,
  eyebrow,
  gap = "lg",
  title,
}: SectionContainerProps) {
  return (
    <Box
      component="section"
      style={{
        width: "100%",
      }}
    >
      <Stack gap={gap}>
        {title || description || eyebrow || actions ? (
          <PageHeader
            actions={actions}
            description={description}
            eyebrow={eyebrow}
            title={title ?? ""}
          />
        ) : null}
        <Box
          style={{
            display: "grid",
            gap: verifyForGoodTokens.spacing.scale.md,
          }}
        >
          {children}
        </Box>
      </Stack>
    </Box>
  );
}
