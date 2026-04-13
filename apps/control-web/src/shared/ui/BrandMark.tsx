import { useState } from "react";

const BRAND_MARK_SOURCES = [
  "/favicon.png",
  "/branding/logo-mark.png",
  "/branding/logo-mark.jpg",
  "/branding/logo-mark.jpeg",
] as const;

const sizeClasses = {
  sm: "h-9 w-9 rounded-xl",
  md: "h-11 w-11 rounded-2xl",
  lg: "h-14 w-14 rounded-[20px]",
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
  alt = "Limiar logo",
}: BrandMarkProps) => {
  const [sourceIndex, setSourceIndex] = useState(0);
  const src = BRAND_MARK_SOURCES[sourceIndex];
  const showImage = sourceIndex < BRAND_MARK_SOURCES.length;

  return (
    <span
      className={`relative inline-flex items-center justify-center border border-limiar-300/20 bg-limiar-400/10 shadow-[0_0_24px_rgba(167,139,250,0.18)] ${sizeClasses[size]} ${className}`}
    >
      {showImage ? (
        <img
          src={src}
          alt={alt}
          onError={() => setSourceIndex((current) => current + 1)}
          className={`h-full w-full object-contain p-1.5 ${imageClassName}`}
        />
      ) : (
        <span className="font-display text-lg font-bold text-limiar-100">LC</span>
      )}
    </span>
  );
};
