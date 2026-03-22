import { useComputedColorScheme } from "@mantine/core";
import {
  verifyForGoodTokens,
  type VerifyForGoodThemeMode,
} from "./tokens";

export function useVerifyForGoodThemeMode() {
  return useComputedColorScheme("light") as VerifyForGoodThemeMode;
}

export function getVerifyForGoodSemanticColors(mode: VerifyForGoodThemeMode) {
  return verifyForGoodTokens.color.semantic[mode];
}

export function useVerifyForGoodSemanticColors() {
  const mode = useVerifyForGoodThemeMode();

  return {
    mode,
    palette: verifyForGoodTokens.color.palette,
    semantic: getVerifyForGoodSemanticColors(mode),
    tokens: verifyForGoodTokens,
  };
}
