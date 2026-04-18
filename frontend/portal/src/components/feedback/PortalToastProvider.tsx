import {
  createContext,
  useContext,
  useMemo,
  useState,
  type PropsWithChildren,
} from "react";

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

  return (
    <PortalToastContext.Provider value={value}>
      {children}
      <div
        aria-atomic="false"
        aria-live="polite"
        className="portal-toast-region"
      >
        {toasts.map((toast) => (
          <div
            className={`portal-toast portal-toast--${toast.tone}`}
            key={toast.id}
            role={toast.tone === "error" ? "alert" : "status"}
          >
            <div className="portal-toast__content">
              <p className="portal-toast__title">{toast.title}</p>
              <p className="portal-toast__message">{toast.message}</p>
            </div>
            <button
              aria-label="Dismiss notification"
              className="portal-toast__dismiss"
              onClick={() => {
                value.dismissToast(toast.id);
              }}
              type="button"
            >
              Dismiss
            </button>
          </div>
        ))}
      </div>
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
