import { useEffect } from "react";

export type ToastVariant = "success" | "error" | "info";

export type ToastState = {
  variant: ToastVariant;
  title: string;
  description?: string;
  duration?: number;
};

type ToastProps = {
  toast: ToastState | null;
  onClose: () => void;
};

const icons: Record<ToastVariant, string> = {
  success: "✅",
  error: "⚠️",
  info: "ℹ️",
};

const ringStyles: Record<ToastVariant, string> = {
  success: "border-emerald-700 bg-emerald-900/20 text-emerald-200",
  error: "border-rose-700 bg-rose-900/20 text-rose-200",
  info: "border-slate-700 bg-slate-900/60 text-slate-200",
};

export const Toast = ({ toast, onClose }: ToastProps) => {
  useEffect(() => {
    if (!toast) {
      return;
    }

    const timeout = window.setTimeout(onClose, toast.duration ?? 3000);
    return () => window.clearTimeout(timeout);
  }, [toast, onClose]);

  if (!toast) {
    return null;
  }

  return (
    <div className="fixed inset-x-4 top-4 z-50 md:inset-x-auto md:right-6">
      <div
        className={`rounded-2xl border px-4 py-3 shadow-lg ${ringStyles[toast.variant]}`}
      >
        <div className="flex items-start gap-3">
          <span className="text-lg">{icons[toast.variant]}</span>
          <div className="flex-1">
            <p className="text-sm font-semibold">{toast.title}</p>
            {toast.description && (
              <p className="mt-1 text-xs text-slate-300">{toast.description}</p>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="text-xs uppercase tracking-[0.2em]"
          >
            ✕
          </button>
        </div>
      </div>
    </div>
  );
};
