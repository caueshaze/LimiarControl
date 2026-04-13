import { type ReactElement } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { routes } from "../../../app/routes/routes";
import { useAuth } from "../hooks/useAuth";

export const RequireAuth = ({ children }: { children: ReactElement }) => {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return null;
  }
  if (!user) {
    return <Navigate to={routes.login} replace state={{ from: location.pathname }} />;
  }

  return children;
};
