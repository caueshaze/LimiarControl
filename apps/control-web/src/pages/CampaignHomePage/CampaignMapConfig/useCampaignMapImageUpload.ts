import { useRef, useState, type ChangeEvent, type Dispatch, type SetStateAction } from "react";
import { uploadRepo } from "../../../shared/api/uploadRepo";
import { useLocale } from "../../../shared/hooks/useLocale";
import type { FormState } from "./types";

export const ACCEPTED_IMAGE_TYPES = "image/jpeg,image/png,image/webp,image/gif";
export const MAX_IMAGE_MB = 30;

const MAX_IMAGE_BYTES = MAX_IMAGE_MB * 1024 * 1024;

type Props = {
  campaignId: string;
  setForm: Dispatch<SetStateAction<FormState>>;
  setError: Dispatch<SetStateAction<string | null>>;
  setSuccess: Dispatch<SetStateAction<string | null>>;
};

export function useCampaignMapImageUpload({
  campaignId,
  setForm,
  setError,
  setSuccess,
}: Props) {
  const { t } = useLocale();
  const imageInputRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);

  const handleChooseImage = () => {
    imageInputRef.current?.click();
  };

  const handleImageSelected = async (event: ChangeEvent<HTMLInputElement>) => {
    const input = event.currentTarget;
    const file = input.files?.[0];
    if (!file) return;

    if (!file.type.startsWith("image/")) {
      setError(t("campaignHome.mapImageTypeError"));
      input.value = "";
      return;
    }

    if (file.size > MAX_IMAGE_BYTES) {
      setError(
        t("campaignHome.mapImageSizeError").replace("{maxMb}", String(MAX_IMAGE_MB)),
      );
      input.value = "";
      return;
    }

    setUploading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await uploadRepo.uploadImage({
        file,
        kind: "campaign_map",
        campaignId,
      });
      setForm((current) => ({ ...current, imageUrl: result.url }));
    } catch (uploadError) {
      setError(
        uploadError instanceof Error
          ? uploadError.message
          : t("campaignHome.mapUploadError"),
      );
    } finally {
      setUploading(false);
      input.value = "";
    }
  };

  return {
    imageInputRef,
    uploading,
    handleChooseImage,
    handleImageSelected,
  };
}
