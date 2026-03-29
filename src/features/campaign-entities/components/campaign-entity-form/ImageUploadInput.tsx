import { useRef, useState } from "react";
import { uploadRepo } from "../../../../shared/api/uploadRepo";

type Props = {
  value: string;
  onChange: (url: string) => void;
  label: string;
  required?: boolean;
};

const ACCEPTED = "image/jpeg,image/png,image/webp,image/gif";
const MAX_MB = 5;
const MAX_BYTES = MAX_MB * 1024 * 1024;

export const ImageUploadInput = ({ value, onChange, label, required }: Props) => {
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
      const result = await uploadRepo.uploadImage(file);
      onChange(result.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Falha ao fazer upload.");
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  return (
    <div className="mt-2">
      <div className="flex items-start gap-3">
        {/* Preview */}
        <div className="shrink-0">
          {value ? (
            <img
              src={value}
              alt={label}
              className="h-20 w-20 rounded-xl border border-slate-700 object-cover"
            />
          ) : (
            <div className="flex h-20 w-20 items-center justify-center rounded-xl border border-dashed border-slate-600 bg-slate-800/50 text-2xl text-slate-500">
              ?
            </div>
          )}
        </div>

        {/* Upload area */}
        <div className="flex-1">
          <button
            type="button"
            onClick={() => inputRef.current?.click()}
            disabled={uploading}
            className="rounded-2xl border border-slate-700 bg-slate-800/60 px-4 py-2.5 text-sm font-medium text-slate-200 transition hover:bg-slate-700/80 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {uploading ? "Enviando..." : value ? "Trocar imagem" : "Escolher imagem"}
          </button>
          <p className="mt-1.5 text-xs text-slate-500">
            JPEG, PNG, WebP ou GIF · máx. {MAX_MB} MB · quadrada 512×512 ou maior recomendado
          </p>
          {error && (
            <p className="mt-1.5 text-xs text-red-400">{error}</p>
          )}
        </div>
      </div>

      {/* Hidden file input — never touched by user directly */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPTED}
        onChange={handleFileChange}
        className="hidden"
        aria-label={label}
        required={required && !value}
      />
    </div>
  );
};
