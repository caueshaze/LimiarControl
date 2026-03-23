import { Suspense, lazy, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AppLayout } from "../../shared/ui/AppLayout";
import { APP_NAME } from "../config/appConfig";
import { routes } from "./routes";
import { RequireAuth, useAuth } from "../../features/auth";
import { useCampaigns } from "../../features/campaign-select";
import type { RoleMode } from "../../shared/types/role";
import { useLocale } from "../../shared/hooks/useLocale";
import { JoinPage } from "../../pages/JoinPage";
import { LandingPage } from "../../pages/LandingPage";
import { LoginPage } from "../../pages/LoginPage";
import { RegisterPage } from "../../pages/RegisterPage";

const CampaignHomePage = lazy(async () => {
  const module = await import("../../pages/CampaignHomePage");
  return { default: module.CampaignHomePage };
});
const CatalogPage = lazy(async () => {
  const module = await import("../../pages/CatalogPage");
  return { default: module.CatalogPage };
});
const GmDashboardPage = lazy(async () => {
  const module = await import("../../pages/GmDashboardPage/GmDashboardPage");
  return { default: module.GmDashboardPage };
});
const GmHomePage = lazy(async () => {
  const module = await import("../../pages/GmHomePage/GmHomePage");
  return { default: module.GmHomePage };
});
const NpcsPage = lazy(async () => {
  const module = await import("../../pages/NpcsPage");
  return { default: module.NpcsPage };
});
const PartyDetailsPage = lazy(async () => {
  const module = await import("../../pages/PartyDetailsPage");
  return { default: module.PartyDetailsPage };
});
const PlayerBoardPage = lazy(async () => {
  const module = await import("../../pages/PlayerBoardPage");
  return { default: module.PlayerBoardPage };
});
const PlayerHomePage = lazy(async () => {
  const module = await import("../../pages/PlayerHomePage/PlayerHomePage");
  return { default: module.PlayerHomePage };
});
const PlayerPartyPage = lazy(async () => {
  const module = await import("../../pages/PlayerPartyPage");
  return { default: module.PlayerPartyPage };
});
const CharacterSheetPage = lazy(async () => {
  const module = await import("../../features/character-sheet");
  return { default: module.CharacterSheetPage };
});

const RequireGmRole = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  if (user?.role !== "GM") {
    return <Navigate to={routes.home} replace />;
  }
  return <>{children}</>;
};

export const AppRoutes = () => {
  const { user, logout } = useAuth();
  const { selectedCampaignId } = useCampaigns();
  const { locale } = useLocale();
  const userRole: RoleMode = user?.role ?? "PLAYER";
  const loadingLabel = locale === "pt" ? "Carregando..." : "Loading...";

  const renderRoute = (children: ReactNode) => (
    <Suspense
      fallback={
        <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,28,0.9),rgba(2,6,23,0.96))] p-5 text-sm text-slate-300">
          {loadingLabel}
        </div>
      }
    >
      {children}
    </Suspense>
  );

  return (
    <Routes>
      <Route path={routes.root} element={<LandingPage />} />
      <Route path={routes.login} element={<LoginPage />} />
      <Route path={routes.register} element={<RegisterPage />} />
      <Route element={<AppLayout title={APP_NAME} user={user ?? undefined} onLogout={logout} />}>
        <Route
          path={routes.home}
          element={
            <RequireAuth>
              {renderRoute(userRole === "PLAYER" ? <PlayerHomePage /> : <GmHomePage />)}
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
                <Navigate
                  to={
                    selectedCampaignId
                      ? routes.campaignEdit.replace(":campaignId", selectedCampaignId)
                      : routes.home
                  }
                  replace
                />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignEdit}
          element={
            <RequireAuth>
              <RequireGmRole>
                {renderRoute(<CampaignHomePage />)}
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.partyDetails}
          element={
            <RequireAuth>
              <RequireGmRole>
                {renderRoute(<PartyDetailsPage />)}
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
                renderRoute(<PlayerPartyPage />)
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
                renderRoute(<PlayerBoardPage />)
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
                {renderRoute(<CatalogPage />)}
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.bestiary}
          element={
            <RequireAuth>
              <RequireGmRole>
                {renderRoute(<NpcsPage />)}
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.npcs}
          element={
            <RequireAuth>
              <RequireGmRole>
                <Navigate to={routes.bestiary} replace />
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignDashboard}
          element={
            <RequireAuth>
              <RequireGmRole>
                {renderRoute(<GmDashboardPage />)}
              </RequireGmRole>
            </RequireAuth>
          }
        />
        <Route
          path={routes.characterSheet}
          element={
            <RequireAuth>
              {renderRoute(
                <CharacterSheetPage viewerUserId={user?.userId ?? null} viewerRole={userRole} />,
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.characterSheetParty}
          element={
            <RequireAuth>
              {renderRoute(
                <CharacterSheetPage viewerUserId={user?.userId ?? null} viewerRole={userRole} />,
              )}
            </RequireAuth>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to={routes.login} replace />} />
    </Routes>
  );
};
