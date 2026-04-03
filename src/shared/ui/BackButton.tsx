import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { navigateBackOrFallback } from "../lib/navigation";

type BackButtonProps = {
  label: ReactNode;
  fallbackTo?: string | null;
  className?: string;
  replace?: boolean;
};

export const BackButton = ({
  label,
  fallbackTo = null,
  className = "",
  replace = false,
}: BackButtonProps) => {
  const navigate = useNavigate();

  const handleClick = () => {
    navigateBackOrFallback(navigate, { fallbackTo, replace });
  };

  return (
    <button type="button" onClick={handleClick} className={className}>
      {label}
    </button>
  );
};
