import { useRef, useState } from "react";
import { uploadRepo } from "../../../shared/api/uploadRepo";
import { ManagedImage } from "../../../shared/ui";

const PRESET_COLORS = [
  "#8b5cf6", // limiar
  "#3b82f6", // blue
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#ec4899", // pink
  "#06b6d4", // cyan
  "#84cc16", // lime
];

const PRESET_TOKENS = [
  "/onboarding/tokens/token-01.png",
  "/onboarding/tokens/token-02.png",
  "/onboarding/tokens/token-03.png",
  "/onboarding/tokens/token-04.png",
  "/onboarding/tokens/token-05.png",
  "/onboarding/tokens/token-06.png",
];

type Tab = "color" | "image";

type StepTokenProps = {
  tokenColor: string | null;
  tokenImageUrl: string | null;
  onColorChange: (value: string | null) => void;
  onImageChange: (value: string | null) => void;
  onBack: () => void;
  onNext: () => void;
};

export const StepToken = ({
  tokenColor,
  tokenImageUrl,
  onColorChange,
  onImageChange,
  onBack,
  onNext,
}: StepTokenProps) => {
  const [tab, setTab] = useState<Tab>(tokenImageUrl ? "image" : "color");
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadRepo.uploadImage({ file, kind: "user_token" });
      onImageChange(result.url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha no upload.";
      setUploadError(message);
    } finally {
      setUploading(false);
    }
  };

  const previewColor = tokenColor ?? "#8b5cf6";

  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-300">
        Passo 2 de 2
      </p>
      <h2 className="mt-2 font-display text-3xl font-bold text-white">
        Seu token no mapa
      </h2>
      <p className="mt-2 text-sm text-slate-400">
        Escolha uma cor sólida (visível no combate) ou suba uma imagem.
      </p>

      {/* Preview */}
      <div className="mt-6 flex items-center justify-center">
        <div className="relative h-28 w-28">
          <div
            className="absolute inset-0 rounded-full blur-2xl opacity-50"
            style={{ background: previewColor }}
          />
          <div
            className="relative h-28 w-28 overflow-hidden rounded-full border-2 border-white/20 shadow-[0_8px_32px_rgba(0,0,0,0.5)]"
            style={{ background: previewColor }}
          >
            {tab === "image" && tokenImageUrl && (
              <ManagedImage src={tokenImageUrl} alt="token" className="h-full w-full object-cover" />
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="mt-6 inline-flex w-full overflow-hidden rounded-2xl border border-white/10 text-[11px] font-bold uppercase tracking-[0.2em]">
        <button
          type="button"
          onClick={() => setTab("color")}
          className={`flex-1 py-2.5 transition-colors ${
            tab === "color" ? "bg-white/10 text-white" : "text-slate-500 hover:bg-white/5"
          }`}
        >
          Cor sólida
        </button>
        <button
          type="button"
          onClick={() => setTab("image")}
          className={`flex-1 py-2.5 transition-colors ${
            tab === "image" ? "bg-white/10 text-white" : "text-slate-500 hover:bg-white/5"
          }`}
        >
          Imagem
        </button>
      </div>

      {/* Tab content */}
      <div className="mt-5">
        {tab === "color" ? (
          <div className="grid grid-cols-8 gap-2.5">
            {PRESET_COLORS.map((color, idx) => {
              const isSelected = tokenColor === color;
              return (
                <button
                  key={color}
                  type="button"
                  onClick={() => onColorChange(color)}
                  style={{ animationDelay: `${idx * 40}ms`, animationFillMode: "both", background: color }}
                  className={`animate-[landing-rise_0.4s_ease-out] aspect-square rounded-full border-2 transition-all active:scale-90 ${
                    isSelected
                      ? "border-white shadow-[0_0_20px_rgba(255,255,255,0.4)]"
                      : "border-white/0 hover:border-white/40"
                  }`}
                  aria-label={color}
                />
              );
            })}
          </div>
        ) : (
          <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
            {PRESET_TOKENS.map((preset, idx) => {
              const isSelected = tokenImageUrl === preset;
              return (
                <button
                  key={preset}
                  type="button"
                  onClick={() => onImageChange(preset)}
                  style={{ animationDelay: `${idx * 40}ms`, animationFillMode: "both" }}
                  className={`animate-[landing-rise_0.4s_ease-out] aspect-square overflow-hidden rounded-full border-2 transition-all active:scale-95 ${
                    isSelected
                      ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.5)]"
                      : "border-white/10 hover:border-white/30"
                  }`}
                >
                  <img src={preset} alt={`token ${idx + 1}`} className="h-full w-full object-cover" />
                </button>
              );
            })}

            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              style={{ animationDelay: `${PRESET_TOKENS.length * 40}ms`, animationFillMode: "both" }}
              className={`animate-[landing-rise_0.4s_ease-out] aspect-square overflow-hidden rounded-full border-2 border-dashed transition-all active:scale-95 ${
                tokenImageUrl && !PRESET_TOKENS.includes(tokenImageUrl)
                  ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.5)]"
                  : "border-white/15 hover:border-white/30"
              } ${uploading ? "opacity-60" : ""}`}
            >
              {tokenImageUrl && !PRESET_TOKENS.includes(tokenImageUrl) ? (
                <ManagedImage src={tokenImageUrl} alt="upload" className="h-full w-full object-cover" />
              ) : (
                <div className="flex h-full w-full items-center justify-center text-2xl text-slate-400">
                  +
                </div>
              )}
            </button>
          </div>
        )}

        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handleUpload(file);
            e.target.value = "";
          }}
        />

        {uploadError && <p className="mt-2 text-[11px] text-rose-400">{uploadError}</p>}
      </div>

      {/* Actions */}
      <div className="mt-8 flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="rounded-full border border-white/10 bg-white/5 px-5 py-2.5 text-[11px] font-bold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/20 hover:text-white active:scale-95"
        >
          ← Voltar
        </button>
        <button
          type="button"
          onClick={onNext}
          className="rounded-full bg-gradient-to-r from-limiar-500 to-limiar-400 px-6 py-2.5 text-[11px] font-bold uppercase tracking-[0.24em] text-white shadow-[0_0_20px_rgba(139,92,246,0.4)] transition-all hover:shadow-[0_0_30px_rgba(139,92,246,0.6)] active:scale-95"
        >
          Próximo →
        </button>
      </div>
    </div>
  );
};
