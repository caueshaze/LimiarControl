import { type ImgHTMLAttributes, useEffect, useState } from "react";
import { getToken } from "../auth/tokenStore";

type Props = Omit<ImgHTMLAttributes<HTMLImageElement>, "src"> & {
  src: string;
};

const isManagedAssetUrl = (value: string) => value.startsWith("/api/assets/");

export const ManagedImage = ({ src, ...props }: Props) => {
  const [resolvedSrc, setResolvedSrc] = useState(() =>
    isManagedAssetUrl(src) ? "" : src,
  );

  useEffect(() => {
    if (!src) {
      setResolvedSrc("");
      return;
    }
    if (!isManagedAssetUrl(src)) {
      setResolvedSrc(src);
      return;
    }

    const controller = new AbortController();
    const token = getToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers.Authorization = `Bearer ${token}`;
    }

    let active = true;
    let objectUrl: string | null = null;

    fetch(src, {
      headers,
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`Failed to load asset (${response.status})`);
        }
        return response.blob();
      })
      .then((blob) => {
        if (!active) return;
        objectUrl = URL.createObjectURL(blob);
        setResolvedSrc(objectUrl);
      })
      .catch(() => {
        if (!active) return;
        setResolvedSrc("");
      });

    return () => {
      active = false;
      controller.abort();
      if (objectUrl) {
        URL.revokeObjectURL(objectUrl);
      }
    };
  }, [src]);

  if (!resolvedSrc) {
    return null;
  }

  return <img {...props} src={resolvedSrc} />;
};
