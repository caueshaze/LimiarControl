import { useState } from "react";
import { useLocale } from "../hooks/useLocale";

const BRAND_MARK_SOURCES = [
  "/favicon.png",
  "/branding/logo-mark.png",
  "/branding/logo-mark.jpg",
  "/branding/logo-mark.jpeg",
] as const;

const sizeClasses = {
  sm: "h-14 w-14",
  md: "h-18 w-18",
  lg: "h-22 w-22",
} as const;

type BrandMarkProps = {
  size?: keyof typeof sizeClasses;
  className?: string;
  imageClassName?: string;
  alt?: string;
};

export const BrandMark = ({
  size = "md",
  className = "",
  imageClassName = "",
  alt,
}: BrandMarkProps) => {
  const { t } = useLocale();
  const [sourceIndex, setSourceIndex] = useState(0);
  const src = BRAND_MARK_SOURCES[sourceIndex];
  const showImage = sourceIndex < BRAND_MARK_SOURCES.length;
  const resolvedAlt = alt ?? t("home.landing.logoAlt");

  return (
    <span
      className={`relative inline-flex items-center justify-center ${sizeClasses[size]} ${className}`}
    >
      {showImage ? (
        <img
          src={src}
          alt={resolvedAlt}
          onError={() => setSourceIndex((current) => current + 1)}
          className={`h-full w-full object-contain ${imageClassName}`}
        />
      ) : (
        <span className="font-display text-lg font-bold text-limiar-100">LC</span>
      )}
    </span>
  );
};
