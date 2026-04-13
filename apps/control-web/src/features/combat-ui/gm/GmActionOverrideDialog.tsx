import { useEffect } from "react";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  onConfirm: () => void;
  resourceName?: string;
  isSubmitting?: boolean;
};

export const GmActionOverrideDialog = ({ isOpen, onClose, onConfirm, resourceName, isSubmitting }: Props) => {
  // Prevent scrolling when open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = "hidden";
    } else {
      document.body.style.overflow = "";
    }
    return () => {
      document.body.style.overflow = "";
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm" 
        aria-hidden="true" 
        onClick={isSubmitting ? undefined : onClose}
      />

      {/* Dialog */}
      <div className="relative w-full max-w-md overflow-hidden rounded-3xl border border-rose-500/30 bg-[linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.98))] p-6 text-left shadow-[0_18px_60px_rgba(2,6,23,0.5)]">
        <h3 className="text-lg font-semibold leading-6 text-white text-center">
          Ação Não Permitida Pelo Sistema
        </h3>

        <div className="mt-4">
          <p className="text-sm text-slate-300 text-center">
            Esta entidade já consumiu o recurso <strong className="text-rose-400 font-bold uppercase tracking-wider">{resourceName || "Action"}</strong> neste turno. 
          </p>
          <p className="text-sm text-slate-400 mt-2 text-center">
            Deseja forçar a ação mesmo assim, ignorando o limite e registrando a exceção no log de combate do GM?
          </p>
        </div>

        <div className="mt-6 flex justify-center gap-3">
          <button
            type="button"
            disabled={isSubmitting}
            className="inline-flex justify-center rounded-2xl border border-white/10 bg-slate-800/50 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-700/50 disabled:opacity-50"
            onClick={onClose}
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={isSubmitting}
            className="inline-flex justify-center rounded-2xl border border-rose-500/50 bg-rose-600/50 px-4 py-2 text-sm font-semibold text-rose-100 hover:bg-rose-500/80 disabled:opacity-50"
            onClick={onConfirm}
          >
            Confirmar (Forçar Ação)
          </button>
        </div>
      </div>
    </div>
  );
};
