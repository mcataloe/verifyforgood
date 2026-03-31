import type { ComponentProps } from "react";
import { DetailPageLayout } from "./DetailPageLayout";

export type StackedDetailSectionsProps = ComponentProps<typeof DetailPageLayout>;

export function StackedDetailSections(props: StackedDetailSectionsProps) {
  return <DetailPageLayout {...props} />;
}
