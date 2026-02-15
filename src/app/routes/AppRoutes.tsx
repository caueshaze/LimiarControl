import type { ReactNode } from "react";
import { Navigate, Route, Routes, useParams } from "react-router-dom";
import { useEffect } from "react";
import { AppLayout } from "../../shared/ui/AppLayout";
import { APP_NAME } from "../config/appConfig";
import {
  CampaignHomePage,
  CampaignSelectPage,
  CatalogPage,
  GmHomePage,
  GmDashboardPage,
  GmSessionsPage,
  InventoryPage,
  JoinPage,
  LoginPage,
  RegisterPage,
  NpcsPage,
  RollsPage,
  ShopPage,
  PlayerBoardPage,
  PlayerHomePage,
} from "../../pages";
import { routes } from "./routes";
import { useCampaignMember, useCampaigns } from "../../features/campaign-select";
import { RequireAuth, useAuth } from "../../features/auth";
import type { RoleMode } from "../../shared/types/role";

const CampaignHomeRoute = ({ userRole }: { userRole: RoleMode }) => {
  const { selectedCampaignId } = useCampaigns();
  const { memberRole, loading: memberLoading, loaded: memberLoaded } =
    useCampaignMember(selectedCampaignId);
  if (userRole !== "PLAYER") {
    return <Navigate to={routes.gmHome} replace />;
  }
  if (!selectedCampaignId) {
    return <Navigate to={routes.join} replace />;
  }
  if (memberLoading || !memberLoaded) {
    return null;
  }
  if (!memberRole) {
    return <Navigate to={routes.join} replace />;
  }
  return <Navigate to={routes.board.replace(":campaignId", selectedCampaignId)} replace />;
};

const RequireCampaignGmParam = ({ children }: { children: ReactNode }) => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const { selectedCampaignId, selectCampaign } = useCampaigns();
  const { memberRole, loading: memberLoading, loaded: memberLoaded } =
    useCampaignMember(campaignId);
  if (!campaignId) {
    return <Navigate to={routes.gmHome} replace />;
  }
  useEffect(() => {
    if (campaignId && selectedCampaignId !== campaignId) {
      selectCampaign(campaignId);
    }
  }, [campaignId, selectedCampaignId, selectCampaign]);
  if (memberLoading || !memberLoaded) {
    return null;
  }
  if (!memberRole || memberRole !== "GM") {
    return <Navigate to={routes.gmHome} replace />;
  }
  return <>{children}</>;
};

const RequireCampaignPlayerParam = ({ children }: { children: ReactNode }) => {
  const { campaignId } = useParams<{ campaignId: string }>();
  const { selectedCampaignId, setSelectedCampaignLocal } = useCampaigns();
  const { memberRole, loading: memberLoading, loaded: memberLoaded } =
    useCampaignMember(campaignId);
  if (!campaignId) {
    return <Navigate to={routes.join} replace />;
  }
  useEffect(() => {
    if (campaignId && selectedCampaignId !== campaignId) {
      setSelectedCampaignLocal(campaignId);
    }
  }, [campaignId, selectedCampaignId, setSelectedCampaignLocal]);
  if (memberLoading || !memberLoaded) {
    return null;
  }
  if (!memberRole) {
    return <Navigate to={routes.join} replace />;
  }
  return <>{children}</>;
};

const RootRoute = ({ userRole }: { userRole: RoleMode }) => {
  return (
    <Navigate to={userRole === "PLAYER" ? routes.playerHome : routes.gmHome} replace />
  );
};

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
              <RootRoute userRole={userRole} />
            </RequireAuth>
          }
        />
        <Route
          path={routes.home}
          element={
            <RequireAuth>
              <RootRoute userRole={userRole} />
            </RequireAuth>
          }
        />
        <Route
          path={routes.gmHome}
          element={
            <RequireAuth>
              {userRole === "GM" ? <GmHomePage /> : <Navigate to={routes.playerHome} replace />}
            </RequireAuth>
          }
        />
        <Route
          path={routes.playerHome}
          element={
            <RequireAuth>
              {userRole === "PLAYER" ? (
                <PlayerHomePage />
              ) : (
                <Navigate to={routes.gmHome} replace />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignHome}
          element={
            <RequireAuth>
              <CampaignHomeRoute userRole={userRole} />
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaigns}
          element={
            <RequireAuth>
              {userRole === "PLAYER" ? (
                <Navigate to={routes.playerHome} replace />
              ) : (
                <CampaignSelectPage />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignDetails}
          element={
            <RequireAuth>
              <RequireCampaignGmParam>
                <CampaignHomePage />
              </RequireCampaignGmParam>
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
          path={routes.shop}
          element={
            <RequireAuth>
              {userRole === "GM" ? (
                <ShopPage />
              ) : (
                <Navigate to={routes.campaignHome} replace />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.rolls}
          element={
            <RequireAuth>
              {userRole === "GM" ? (
                <RollsPage />
              ) : (
                <Navigate to={routes.campaignHome} replace />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.catalog}
          element={
            <RequireAuth>
              <RequireCampaignGmParam>
                <CatalogPage />
              </RequireCampaignGmParam>
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignSessions}
          element={
            <RequireAuth>
              <RequireCampaignGmParam>
                <GmSessionsPage />
              </RequireCampaignGmParam>
            </RequireAuth>
          }
        />
        <Route
          path={routes.board}
          element={
            <RequireAuth>
              {userRole === "PLAYER" ? (
                <RequireCampaignPlayerParam>
                  <PlayerBoardPage />
                </RequireCampaignPlayerParam>
              ) : (
                <Navigate to={routes.gmHome} replace />
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.gmDashboard}
          element={
            <RequireAuth>
              <RequireCampaignGmParam>
                <GmDashboardPage />
              </RequireCampaignGmParam>
            </RequireAuth>
          }
        />
        <Route
          path={routes.inventory}
          element={
            <RequireAuth>
              <InventoryPage />
            </RequireAuth>
          }
        />
        <Route
          path={routes.npcs}
          element={
            <RequireAuth>
              <RequireCampaignGmParam>
                <NpcsPage />
              </RequireCampaignGmParam>
            </RequireAuth>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to={routes.login} replace />} />
    </Routes>
  );
};
