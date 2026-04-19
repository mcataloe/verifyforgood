import {
  createContext,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";
import { createPortal } from "react-dom";
import { CloseButton, Paper, Stack, Text } from "@mantine/core";

export type PortalToastTone = "error" | "success" | "warning";

export interface PortalToastInput {
  id?: string;
  message: string;
  title?: string;
  tone: PortalToastTone;
}

interface PortalToastRecord extends Required<PortalToastInput> {}

interface PortalToastContextValue {
  dismissToast: (id: string) => void;
  showToast: (input: PortalToastInput) => string;
}

const PortalToastContext = createContext<PortalToastContextValue>({
  dismissToast: () => {},
  showToast: () => "",
});

export function PortalToastProvider({ children }: PropsWithChildren) {
  const [toasts, setToasts] = useState<PortalToastRecord[]>([]);

  const value = useMemo<PortalToastContextValue>(
    () => ({
      dismissToast: (id) => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
      },
      showToast: (input) => {
        const id = input.id ?? `toast_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
        const nextToast: PortalToastRecord = {
          id,
          message: input.message,
          title: input.title ?? defaultToastTitle(input.tone),
          tone: input.tone,
        };
        setToasts((current) => {
          const remaining = current.filter((toast) => toast.id !== id);
          return [...remaining, nextToast];
        });
        return id;
      },
    }),
    [],
  );

  const toastRegion = (
    <div
      aria-atomic="false"
      aria-live="polite"
      className="portal-toast-region"
    >
      {toasts.map((toast) => (
        <Paper
          key={toast.id}
          p="md"
          radius="md"
          role={toast.tone === "error" ? "alert" : "status"}
          shadow="md"
          style={{
            borderColor: resolveToastBorderColor(toast.tone),
            borderStyle: "solid",
            borderWidth: 1,
          }}
          withBorder
        >
          <div
            style={{
              alignItems: "flex-start",
              display: "flex",
              gap: "0.75rem",
              justifyContent: "space-between",
            }}
          >
            <Stack gap={2} style={{ minWidth: 0 }}>
              <Text fw={700}>{toast.title}</Text>
              <Text size="sm">{toast.message}</Text>
            </Stack>
            <CloseButton
              aria-label="Dismiss notification"
              onClick={() => {
                value.dismissToast(toast.id);
              }}
            />
          </div>
        </Paper>
      ))}
    </div>
  );

  return (
    <PortalToastContext.Provider value={value}>
      {children}
      {typeof document === "undefined"
        ? toastRegion
        : createPortal(toastRegion, document.body)}
    </PortalToastContext.Provider>
  );
}

export function usePortalToast() {
  return useContext(PortalToastContext);
}

function defaultToastTitle(tone: PortalToastTone): string {
  if (tone === "error") {
    return "Something went wrong";
  }
  if (tone === "success") {
    return "Done";
  }
  return "Heads up";
}

function resolveToastBorderColor(tone: PortalToastTone) {
  switch (tone) {
    case "error":
      return "var(--mantine-color-red-4)";
    case "success":
      return "var(--mantine-color-green-4)";
    case "warning":
    default:
      return "var(--mantine-color-teal-4)";
  }
}
