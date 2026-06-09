import { useRef, useState } from "react";
import { uploadRepo } from "../../../shared/api/uploadRepo";
import { ManagedImage } from "../../../shared/ui";

type Props = {
  value: string | null;
  onChange: (url: string | null) => void;
  label: string;
  disabled?: boolean;
};

const ACCEPTED = "image/jpeg,image/png,image/webp,image/gif";
const MAX_MB = 30;
const MAX_BYTES = MAX_MB * 1024 * 1024;

/**
 * Portrait uploader for the character sheet. Uploads with kind="user_avatar"
 * (no campaign/entity scope) and returns a managed asset URL stored in
 * `sheet.avatarUrl`.
 */
export const AvatarUploadInput = ({ value, onChange, label, disabled = false }: Props) => {
  const inputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError("Selecione um arquivo de imagem.");
      return;
    }
    if (file.size > MAX_BYTES) {
      setError(`O arquivo deve ter no máximo ${MAX_MB} MB.`);
      return;
    }

    setError(null);
    setUploading(true);
    try {
      const result = await uploadRepo.uploadImage({ file, kind: "user_avatar" });
      onChange(result.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao fazer upload.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="flex items-start gap-3">
      <div className="shrink-0">
        {value ? (
          <ManagedImage
            src={value}
            alt={label}
            className="h-20 w-20 rounded-full border border-amber-500/40 object-cover"
          />
        ) : (
          <div className="flex h-20 w-20 items-center justify-center rounded-full border border-dashed border-slate-600 bg-slate-800/50 text-2xl text-slate-500">
            ?
          </div>
        )}
      </div>

      <div className="flex-1">
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={disabled || uploading}
            className="rounded-2xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-700/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? "Enviando..." : value ? "Trocar retrato" : "Escolher retrato"}
          </button>
          {value && !disabled ? (
            <button
              type="button"
              onClick={() => onChange(null)}
              className="rounded-2xl border border-slate-700 bg-transparent px-4 py-2.5 text-sm font-medium text-slate-400 transition hover:text-rose-300"
            >
              Remover
            </button>
          ) : null}
        </div>
        <p className="mt-1.5 text-xs text-slate-500">
          JPEG, PNG, WebP ou GIF · máx. {MAX_MB} MB · imagem quadrada recomendada
        </p>
        {error && <p className="mt-1.5 text-xs text-red-400">{error}</p>}
      </div>

      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleFileChange}
        className="hidden"
        aria-label={label}
      />
    </div>
  );
};
