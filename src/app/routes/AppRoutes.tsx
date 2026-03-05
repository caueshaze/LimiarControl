import type { ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../../shared/ui/AppLayout";
import { APP_NAME } from "../config/appConfig";
import {
  CampaignHomePage,
  CampaignSelectPage,
  CatalogPage,
  GmDashboardPage,
  GmHomePage,
  JoinPage,
  LoginPage,
  NpcsPage,
  PlayerBoardPage,
  PlayerHomePage,
  RegisterPage,
  PartyDetailsPage,
  PlayerPartyPage,
} from "../../pages";
import { routes } from "./routes";
import { RequireAuth, useAuth } from "../../features/auth";
import type { RoleMode } from "../../shared/types/role";

const RequireGmRole = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  if (user?.role !== "GM") {
    return <Navigate to={routes.home} replace />;
  }
  return <>{children}</>;
};

const RootRoute = () => <Navigate to={routes.home} replace />;

export const AppRoutes = () => {
  const { user, logout } = useAuth();
  const userRole: RoleMode = user?.role ?? "PLAYER";
  return (
    <Routes>
      <Route path={routes.login} element={<LoginPage />} />
      <Route path={routes.register} element={<RegisterPage />} />
      <Route element={<AppLayout title={APP_NAME} user={user ?? undefined} onLogout={logout} />}>
        <Route
          path={routes.root}
          element={
            <RequireAuth>
              <RootRoute />
            </RequireAuth>
          }
        />
        <Route
          path={routes.home}
          element={
            <RequireAuth>
              {userRole === "PLAYER" ? <PlayerHomePage /> : <GmHomePage />}
            </RequireAuth>
          }
        />
        <Route
          path={routes.gmHome}
          element={
            <RequireAuth>
              <RequireGmRole>
                <Navigate to={routes.home} replace />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaigns}
          element={
            <RequireAuth>
              <RequireGmRole>
                <CampaignSelectPage />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignEdit}
          element={
            <RequireAuth>
              <RequireGmRole>
                <CampaignHomePage />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.partyDetails}
          element={
            <RequireAuth>
              <RequireGmRole>
                <PartyDetailsPage />
              </RequireGmRole>
            </RequireAuth>
          }
        />

        <Route
          path={routes.join}
          element={
            <RequireAuth>
              <JoinPage />
            </RequireAuth>
          }
        />
        <Route
          path={routes.playerPartyDetails}
          element={
            <RequireAuth>
              {userRole === "PLAYER" ? (
                <PlayerPartyPage />
              ) : (
                <Navigate to={routes.gmHome} replace />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.board}
          element={
            <RequireAuth>
              {userRole === "PLAYER" ? (
                <PlayerBoardPage />
              ) : (
                <Navigate to={routes.gmHome} replace />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.catalog}
          element={
            <RequireAuth>
              <RequireGmRole>
                <CatalogPage />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.npcs}
          element={
            <RequireAuth>
              <RequireGmRole>
                <NpcsPage />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignDashboard}
          element={
            <RequireAuth>
              <RequireGmRole>
                <GmDashboardPage />
              </RequireGmRole>
            </RequireAuth>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to={routes.login} replace />} />
    </Routes>
  );
};
