import { Suspense, lazy, type ReactNode } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { AdminLayout, AppLayout } from "../../shared/ui";
import { APP_NAME } from "../config/appConfig";
import { routes } from "./routes";
import { RequireAuth, useAuth } from "../../features/auth";
import { useCampaigns } from "../../features/campaign-select";
import { useLocale } from "../../shared/hooks/useLocale";
import { JoinPage } from "../../pages/JoinPage";
import { LandingPage } from "../../pages/LandingPage";
import { LoginPage } from "../../pages/LoginPage";
import { RegisterPage } from "../../pages/RegisterPage";
import { WelcomePage } from "../../pages/WelcomePage";

const CampaignHomePage = lazy(async () => {
  const module = await import("../../pages/CampaignHomePage");
  return { default: module.CampaignHomePage };
});
const CampaignMapsPage = lazy(async () => {
  const module = await import("../../pages/CampaignHomePage");
  return { default: module.CampaignMapsPage };
});
const CatalogPage = lazy(async () => {
  const module = await import("../../pages/CatalogPage");
  return { default: module.CatalogPage };
});
const CatalogItemsPage = lazy(async () => {
  const module = await import("../../pages/CatalogPage");
  return { default: module.CatalogItemsPage };
});
const CatalogSpellsPage = lazy(async () => {
  const module = await import("../../pages/CatalogPage");
  return { default: module.CatalogSpellsPage };
});
const CatalogSpellNewPage = lazy(async () => {
  const module = await import("../../pages/CatalogPage/CatalogSpellNewPage");
  return { default: module.CatalogSpellNewPage };
});
const CatalogSpellEditPage = lazy(async () => {
  const module = await import("../../pages/CatalogPage/CatalogSpellEditPage");
  return { default: module.CatalogSpellEditPage };
});
const SystemCatalogPage = lazy(async () => {
  const module = await import("../../pages/SystemCatalogPage");
  return { default: module.SystemCatalogPage };
});
const SystemSpellCatalogPage = lazy(async () => {
  const module = await import("../../pages/SystemSpellCatalogPage");
  return { default: module.SystemSpellCatalogPage };
});
const GmDashboardPage = lazy(async () => {
  const module = await import("../../pages/GmDashboardPage/GmDashboardPage");
  return { default: module.GmDashboardPage };
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
const UnifiedHomePage = lazy(async () => {
  const module = await import("../../pages/UnifiedHomePage/UnifiedHomePage");
  return { default: module.UnifiedHomePage };
});
const PlayerPartyPage = lazy(async () => {
  const module = await import("../../pages/PlayerPartyPage");
  return { default: module.PlayerPartyPage };
});
const ProfilePage = lazy(async () => {
  const module = await import("../../pages/ProfilePage/ProfilePage");
  return { default: module.ProfilePage };
});
const CharacterSheetPage = lazy(async () => {
  const module = await import("../../features/character-sheet");
  return { default: module.CharacterSheetPage };
});
const CharacterSheetDraftPage = lazy(async () => {
  const module = await import("../../features/character-sheet");
  return { default: module.CharacterSheetDraftPage };
});
const AdminHomePage = lazy(async () => {
  const module = await import("../../pages/AdminHomePage");
  return { default: module.AdminHomePage };
});
const AdminUsersPage = lazy(async () => {
  const module = await import("../../pages/AdminUsersPage");
  return { default: module.AdminUsersPage };
});
const AdminCampaignsPage = lazy(async () => {
  const module = await import("../../pages/AdminCampaignsPage");
  return { default: module.AdminCampaignsPage };
});
const AdminDiagnosticsPage = lazy(async () => {
  const module = await import("../../pages/AdminDiagnosticsPage");
  return { default: module.AdminDiagnosticsPage };
});

const RequireSystemAdmin = ({ children }: { children: ReactNode }) => {
  const { user } = useAuth();
  if (!user?.isSystemAdmin) {
    return <Navigate to={routes.home} replace />;
  }
  return <>{children}</>;
};

export const AppRoutes = () => {
  const { user, logout } = useAuth();
  const { selectedCampaignId } = useCampaigns();
  const { locale } = useLocale();
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
      <Route
        path={routes.welcome}
        element={
          <RequireAuth>
            <WelcomePage />
          </RequireAuth>
        }
      />
      <Route element={<AppLayout title={APP_NAME} user={user ?? undefined} onLogout={logout} />}>
        {/* Home — unified for all users */}
        <Route
          path={routes.home}
          element={
            <RequireAuth>
              {renderRoute(<UnifiedHomePage />)}
            </RequireAuth>
          }
        />
        {/* Legacy /gm and /workspace routes redirect to unified home */}
        <Route
          path={routes.gmHome}
          element={<Navigate to={routes.home} replace />}
        />
        <Route
          path={routes.workspaceHome}
          element={<Navigate to={routes.home} replace />}
        />

        {/* Campaign management — open to any authenticated user */}
        <Route
          path={routes.campaigns}
          element={
            <RequireAuth>
              <Navigate
                to={
                  selectedCampaignId
                    ? routes.campaignEdit.replace(":campaignId", selectedCampaignId)
                    : routes.home
                }
                replace
              />
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignEdit}
          element={
            <RequireAuth>
              {renderRoute(<CampaignHomePage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignMaps}
          element={
            <RequireAuth>
              {renderRoute(<CampaignMapsPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.profile}
          element={
            <RequireAuth>
              {renderRoute(<ProfilePage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.userProfile}
          element={
            <RequireAuth>
              {renderRoute(<ProfilePage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.partyDetails}
          element={
            <RequireAuth>
              {renderRoute(<PartyDetailsPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.gmPartyCharacterSheetDraftNew}
          element={
            <RequireAuth>
              {renderRoute(<CharacterSheetDraftPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.gmPartyCharacterSheetDraft}
          element={
            <RequireAuth>
              {renderRoute(<CharacterSheetDraftPage />)}
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
              {renderRoute(<PlayerPartyPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.board}
          element={
            <RequireAuth>
              {renderRoute(<PlayerBoardPage />)}
            </RequireAuth>
          }
        />

        {/* Catalog — open to any authenticated user; API handles mutation auth */}
        <Route
          path={routes.catalog}
          element={
            <RequireAuth>
              {renderRoute(<CatalogPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.catalogItems}
          element={
            <RequireAuth>
              {renderRoute(<CatalogItemsPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.catalogSpells}
          element={
            <RequireAuth>
              {renderRoute(<CatalogSpellsPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.catalogSpellNew}
          element={
            <RequireAuth>
              {renderRoute(<CatalogSpellNewPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.catalogSpellEdit}
          element={
            <RequireAuth>
              {renderRoute(<CatalogSpellEditPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.bestiary}
          element={
            <RequireAuth>
              {renderRoute(<NpcsPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.npcs}
          element={
            <RequireAuth>
              <Navigate to={routes.bestiary} replace />
            </RequireAuth>
          }
        />
        <Route
          path={routes.campaignDashboard}
          element={
            <RequireAuth>
              {renderRoute(<GmDashboardPage />)}
            </RequireAuth>
          }
        />
        <Route
          path={routes.characterSheet}
          element={
            <RequireAuth>
              {renderRoute(
                <CharacterSheetPage viewerUserId={user?.userId ?? null} viewerRole={user?.role ?? "PLAYER"} />,
              )}
            </RequireAuth>
          }
        />
        <Route
          path={routes.characterSheetParty}
          element={
            <RequireAuth>
              {renderRoute(
                <CharacterSheetPage viewerUserId={user?.userId ?? null} viewerRole={user?.role ?? "PLAYER"} />,
              )}
            </RequireAuth>
          }
        />
      </Route>
      <Route element={<AdminLayout user={user ?? undefined} onLogout={logout} />}>
        <Route
          path={routes.adminHome}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<AdminHomePage />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.systemCatalogAdmin}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<Navigate to={routes.adminCatalogItems} replace />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.systemSpellCatalogAdmin}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<Navigate to={routes.adminCatalogSpells} replace />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.adminCatalogItems}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<SystemCatalogPage />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.adminCatalogSpells}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<SystemSpellCatalogPage />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.adminUsers}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<AdminUsersPage />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.adminCampaigns}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<AdminCampaignsPage />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
        <Route
          path={routes.adminDiagnostics}
          element={
            <RequireAuth>
              <RequireSystemAdmin>
                {renderRoute(<AdminDiagnosticsPage />)}
              </RequireSystemAdmin>
            </RequireAuth>
          }
        />
      </Route>
      <Route path="*" element={<Navigate to={routes.login} replace />} />
    </Routes>
  );
};
