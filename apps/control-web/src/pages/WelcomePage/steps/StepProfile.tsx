import { useRef, useState } from "react";
import { uploadRepo } from "../../../shared/api/uploadRepo";
import { ManagedImage } from "../../../shared/ui";

const PRESET_AVATARS = [
  "/onboarding/avatars/avatar-01.png",
  "/onboarding/avatars/avatar-02.png",
  "/onboarding/avatars/avatar-03.png",
  "/onboarding/avatars/avatar-04.svg",
  "/onboarding/avatars/avatar-05.png",
  "/onboarding/avatars/avatar-06.png",
  "/onboarding/avatars/avatar-07.png",
  "/onboarding/avatars/avatar-08.png",
  "/onboarding/avatars/avatar-09.png",
  "/onboarding/avatars/avatar-10.png",
  "/onboarding/avatars/avatar-11.png",
  "/onboarding/avatars/avatar-12.png",
  "/onboarding/avatars/avatar-13.png",
  "/onboarding/avatars/avatar-14.png",
  "/onboarding/avatars/avatar-15.png",
  "/onboarding/avatars/avatar-16.png",
  "/onboarding/avatars/avatar-17.png",
  "/onboarding/avatars/avatar-18.png",
  "/onboarding/avatars/avatar-19.png",
  "/onboarding/avatars/avatar-20.png",
  "/onboarding/avatars/avatar-21.png",
];

type StepProfileProps = {
  nickname: string;
  avatarUrl: string | null;
  onNicknameChange: (value: string) => void;
  onAvatarChange: (value: string | null) => void;
  onBack: () => void;
  onNext: () => void;
};

export const StepProfile = ({
  nickname,
  avatarUrl,
  onNicknameChange,
  onAvatarChange,
  onBack,
  onNext,
}: StepProfileProps) => {
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const handleUpload = async (file: File) => {
    setUploading(true);
    setUploadError(null);
    try {
      const result = await uploadRepo.uploadImage({ file, kind: "user_avatar" });
      onAvatarChange(result.url);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha no upload.";
      setUploadError(message);
    } finally {
      setUploading(false);
    }
  };

  const canProceed = nickname.trim().length > 0;

  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-300">
        Passo 1 de 2
      </p>
      <h2 className="mt-2 font-display text-3xl font-bold text-white">
        Seu nick e sua foto
      </h2>
      <p className="mt-2 text-sm text-slate-400">
        É assim que o grupo vai te enxergar.
      </p>

      {/* Nickname */}
      <div className="mt-6">
        <label className="text-[10px] font-bold uppercase tracking-[0.28em] text-slate-400">
          Nickname
        </label>
        <input
          type="text"
          value={nickname}
          onChange={(e) => onNicknameChange(e.target.value)}
          maxLength={64}
          placeholder="Como você quer ser chamado"
          className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-600 transition focus:border-limiar-500 focus:outline-none"
        />
      </div>

      {/* Avatar grid */}
      <div className="mt-6">
        <label className="text-[10px] font-bold uppercase tracking-[0.28em] text-slate-400">
          Foto de perfil
        </label>
        <div className="mt-3 grid grid-cols-5 gap-3 sm:grid-cols-7">
          {PRESET_AVATARS.map((preset, idx) => {
            const isSelected = avatarUrl === preset;
            return (
              <button
                key={preset}
                type="button"
                onClick={() => onAvatarChange(preset)}
                style={{ animationDelay: `${idx * 40}ms`, animationFillMode: "both" }}
                className={`animate-[landing-rise_0.4s_ease-out] aspect-square overflow-hidden rounded-2xl border-2 transition-all active:scale-95 ${
                  isSelected
                    ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.5)]"
                    : "border-white/10 hover:border-white/30"
                }`}
              >
                <img src={preset} alt={`avatar ${idx + 1}`} className="h-full w-full object-cover" />
              </button>
            );
          })}

          {/* Upload tile */}
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            style={{ animationDelay: `${PRESET_AVATARS.length * 40}ms`, animationFillMode: "both" }}
            className={`animate-[landing-rise_0.4s_ease-out] aspect-square overflow-hidden rounded-2xl border-2 border-dashed transition-all active:scale-95 ${
              avatarUrl && !PRESET_AVATARS.includes(avatarUrl)
                ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.5)]"
                : "border-white/15 hover:border-white/30"
            } ${uploading ? "opacity-60" : ""}`}
          >
            {avatarUrl && !PRESET_AVATARS.includes(avatarUrl) ? (
              <ManagedImage src={avatarUrl} alt="upload" className="h-full w-full object-cover" />
            ) : (
              <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-slate-400">
                <span className="text-2xl">+</span>
                <span className="text-[9px] font-bold uppercase tracking-[0.18em]">
                  {uploading ? "..." : "Upload"}
                </span>
              </div>
            )}
          </button>
        </div>

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

        {uploadError && (
          <p className="mt-2 text-[11px] text-rose-400">{uploadError}</p>
        )}
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
          disabled={!canProceed}
          className="rounded-full bg-gradient-to-r from-limiar-500 to-limiar-400 px-6 py-2.5 text-[11px] font-bold uppercase tracking-[0.24em] text-white shadow-[0_0_20px_rgba(139,92,246,0.4)] transition-all hover:shadow-[0_0_30px_rgba(139,92,246,0.6)] active:scale-95 disabled:cursor-not-allowed disabled:opacity-40 disabled:shadow-none"
        >
          Próximo →
        </button>
      </div>
    </div>
  );
};
