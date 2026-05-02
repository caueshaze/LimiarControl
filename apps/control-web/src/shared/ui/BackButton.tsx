import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { navigateBackOrFallback } from "../lib/navigation";

type BackButtonProps = {
  label: ReactNode;
  fallbackTo?: string | null;
  className?: string;
  replace?: boolean;
  forceFallback?: boolean;
};

export const BackButton = ({
  label,
  fallbackTo = null,
  className = "",
  replace = false,
  forceFallback = false,
}: BackButtonProps) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (forceFallback && fallbackTo) {
      navigate(fallbackTo, replace ? { replace: true } : undefined);
      return;
    }
    navigateBackOrFallback(navigate, { fallbackTo, replace });
  };

  return (
    <button type="button" onClick={handleClick} className={className}>
      {label}
    </button>
  );
};
