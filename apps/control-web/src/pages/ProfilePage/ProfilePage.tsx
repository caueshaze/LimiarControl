import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { uploadRepo } from "../../shared/api/uploadRepo";
import { type UserProfile, usersRepo } from "../../shared/api/usersRepo";
import { useLocale } from "../../shared/hooks/useLocale";
import { workspaceModeStorage } from "../../shared/lib/workspaceMode";
import type { RoleMode } from "../../shared/types/role";
import { BackButton, ManagedImage } from "../../shared/ui";

const PRESET_AVATARS = [
  "/onboarding/avatars/avatar-01.png",
  "/onboarding/avatars/avatar-02.png",
  "/onboarding/avatars/avatar-03.png",
  "/onboarding/avatars/avatar-04.svg",
  "/onboarding/avatars/avatar-05.png",
  "/onboarding/avatars/avatar-06.png",
  "/onboarding/avatars/avatar-07.png",
  "/onboarding/avatars/avatar-08.png",
  "/onboarding/avatars/avatar-09.png",
  "/onboarding/avatars/avatar-10.png",
  "/onboarding/avatars/avatar-11.png",
  "/onboarding/avatars/avatar-12.png",
  "/onboarding/avatars/avatar-13.png",
  "/onboarding/avatars/avatar-14.png",
  "/onboarding/avatars/avatar-15.png",
  "/onboarding/avatars/avatar-16.png",
  "/onboarding/avatars/avatar-17.png",
  "/onboarding/avatars/avatar-18.png",
  "/onboarding/avatars/avatar-19.png",
  "/onboarding/avatars/avatar-20.png",
  "/onboarding/avatars/avatar-21.png",
];

const PRESET_COLORS = [
  "#8b5cf6",
  "#3b82f6",
  "#10b981",
  "#f59e0b",
  "#ef4444",
  "#ec4899",
  "#06b6d4",
  "#84cc16",
];

const PRESET_TOKENS = [
  "/onboarding/tokens/token-01.png",
  "/onboarding/tokens/token-02.png",
  "/onboarding/tokens/token-03.png",
  "/onboarding/tokens/token-04.png",
  "/onboarding/tokens/token-05.png",
  "/onboarding/tokens/token-06.png",
];

type TokenTab = "color" | "image";

export const ProfilePage = () => {
  const { userId } = useParams<{ userId?: string }>();
  const { user, updateProfile } = useAuth();
  const { t } = useLocale();
  const isOwnProfile = !userId || userId === user?.userId;

  const [loading, setLoading] = useState(!isOwnProfile);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState<string | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);

  const [nickname, setNickname] = useState("");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [tokenColor, setTokenColor] = useState<string | null>(null);
  const [tokenImageUrl, setTokenImageUrl] = useState<string | null>(null);
  const [preferredMode, setPreferredMode] = useState<RoleMode>("PLAYER");
  const [tokenTab, setTokenTab] = useState<TokenTab>("color");
  const [avatarUploadError, setAvatarUploadError] = useState<string | null>(null);
  const [tokenUploadError, setTokenUploadError] = useState<string | null>(null);
  const [avatarUploading, setAvatarUploading] = useState(false);
  const [tokenUploading, setTokenUploading] = useState(false);

  const avatarInputRef = useRef<HTMLInputElement | null>(null);
  const tokenInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (!isOwnProfile) {
      return;
    }
    if (!user) {
      return;
    }

    setProfile({
      id: user.userId,
      displayName: user.displayName || user.username,
      username: user.username,
      avatarUrl: user.avatarUrl,
      tokenColor: user.tokenColor,
      tokenImageUrl: user.tokenImageUrl,
      preferredWorkspaceMode: user.preferredWorkspaceMode,
    });
    setNickname(user.displayName || user.username);
    setAvatarUrl(user.avatarUrl ?? null);
    setTokenColor(user.tokenColor ?? null);
    setTokenImageUrl(user.tokenImageUrl ?? null);
    setPreferredMode(user.preferredWorkspaceMode ?? "PLAYER");
    setTokenTab(user.tokenImageUrl ? "image" : "color");
    setLoadError(null);
  }, [isOwnProfile, user]);

  useEffect(() => {
    if (isOwnProfile || !userId) {
      return;
    }

    setLoading(true);
    setLoadError(null);
    void usersRepo.getProfile(userId)
      .then((nextProfile) => {
        setProfile(nextProfile);
        setNickname(nextProfile.displayName);
        setAvatarUrl(nextProfile.avatarUrl ?? null);
        setTokenColor(nextProfile.tokenColor ?? null);
        setTokenImageUrl(nextProfile.tokenImageUrl ?? null);
        setPreferredMode(nextProfile.preferredWorkspaceMode ?? "PLAYER");
        setTokenTab(nextProfile.tokenImageUrl ? "image" : "color");
      })
      .catch((error: unknown) => {
        const status = (error as { status?: number })?.status;
        setLoadError(status === 404 ? t("profile.notFound") : t("profile.loadError"));
      })
      .finally(() => setLoading(false));
  }, [isOwnProfile, t, userId]);

  const previewColor = tokenColor ?? "#8b5cf6";
  const displayName = profile?.displayName || nickname || user?.displayName || user?.username || "";

  const handleAvatarUpload = async (file: File) => {
    setAvatarUploading(true);
    setAvatarUploadError(null);
    try {
      const result = await uploadRepo.uploadImage({ file, kind: "user_avatar" });
      setAvatarUrl(result.url);
    } catch (error) {
      setAvatarUploadError(error instanceof Error ? error.message : t("profile.saveError"));
    } finally {
      setAvatarUploading(false);
    }
  };

  const handleTokenUpload = async (file: File) => {
    setTokenUploading(true);
    setTokenUploadError(null);
    try {
      const result = await uploadRepo.uploadImage({ file, kind: "user_token" });
      setTokenImageUrl(result.url);
      setTokenTab("image");
    } catch (error) {
      setTokenUploadError(error instanceof Error ? error.message : t("profile.saveError"));
    } finally {
      setTokenUploading(false);
    }
  };

  const handleSave = async () => {
    if (!user?.userId) {
      return;
    }
    setSaving(true);
    setSaveError(null);
    setSaveSuccess(null);
    workspaceModeStorage.writeLegacyMode(preferredMode, user.userId);
    const saved = await updateProfile({
      displayName: nickname.trim() || undefined,
      avatarUrl,
      tokenColor: tokenTab === "color" ? tokenColor : tokenColor,
      tokenImageUrl: tokenTab === "image" ? tokenImageUrl : tokenImageUrl,
      preferredWorkspaceMode: preferredMode,
    });
    setSaving(false);
    if (!saved) {
      setSaveError(t("profile.saveError"));
      return;
    }
    workspaceModeStorage.clearLegacyMode();
    setSaveSuccess(t("profile.saved"));
  };

  const roleBadgeLabel = useMemo(
    () => (preferredMode === "GM" ? t("profile.preferenceGM") : t("profile.preferencePlayer")),
    [preferredMode, t],
  );

  if (loading) {
    return (
      <section className="rounded-[32px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6 text-sm text-slate-300">
        {t("profile.loading")}
      </section>
    );
  }

  if (loadError) {
    return (
      <section className="rounded-[32px] border border-rose-500/20 bg-rose-500/10 p-6 text-sm text-rose-200">
        {loadError}
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div>
        <BackButton
          fallbackTo={routes.home}
          label={<><span aria-hidden>←</span>{t("campaignHome.back")}</>}
          className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/3 px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/16 hover:text-white"
        />
      </div>

      <div className="relative overflow-hidden rounded-[34px] border border-white/8 bg-[#070712] px-6 py-8 shadow-[0_30px_90px_rgba(0,0,0,0.28)] sm:px-8">
        <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(56,189,248,0.16),transparent_28%),radial-gradient(circle_at_80%_15%,rgba(139,92,246,0.14),transparent_22%),linear-gradient(180deg,rgba(5,2,15,0.92),rgba(2,6,23,0.98))]" />
        <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex items-center gap-4">
            <div className="flex h-20 w-20 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5 text-2xl font-bold uppercase text-limiar-100">
              {avatarUrl ? (
                <ManagedImage src={avatarUrl} alt={displayName} className="h-full w-full object-cover" />
              ) : (
                displayName.charAt(0) || "?"
              )}
            </div>
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-300">
                {isOwnProfile ? t("profile.title") : t("profile.publicTitle")}
              </p>
              <h1 className="mt-2 text-3xl font-black tracking-tight text-white">{displayName}</h1>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-300">
                {isOwnProfile ? t("profile.subtitle") : t("profile.publicSubtitle")}
              </p>
              <p className="mt-2 text-xs text-slate-500">
                {t("profile.usernameLabel")}: @{profile?.username ?? user?.username}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="relative h-20 w-20">
              <div className="absolute inset-0 rounded-full blur-2xl opacity-50" style={{ background: previewColor }} />
              <div
                className="relative h-20 w-20 overflow-hidden rounded-full border-2 border-white/20"
                style={{ background: previewColor }}
              >
                {tokenImageUrl ? (
                  <ManagedImage src={tokenImageUrl} alt="token" className="h-full w-full object-cover" />
                ) : null}
              </div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
              <p className="text-[10px] font-bold uppercase tracking-[0.22em] text-slate-500">
                {t("profile.preferenceReadOnly")}
              </p>
              <p className="mt-2 text-sm font-semibold text-white">{roleBadgeLabel}</p>
            </div>
          </div>
        </div>
      </div>

      {!isOwnProfile ? (
        <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
          <p className="text-sm text-slate-300">{t("profile.readOnlyHint")}</p>
          <Link
            to={routes.profile}
            className="mt-4 inline-flex rounded-full border border-limiar-400/25 bg-limiar-500/10 px-4 py-2 text-xs font-semibold uppercase tracking-[0.22em] text-limiar-100 transition hover:bg-limiar-500/20"
          >
            {t("profile.viewOwnProfile")}
          </Link>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
              {t("profile.identityEyebrow")}
            </p>
            <h2 className="mt-2 text-2xl font-bold text-white">{t("profile.identityTitle")}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{t("profile.identityDescription")}</p>

            <div className="mt-6">
              <label className="text-[10px] font-bold uppercase tracking-[0.28em] text-slate-400">
                {t("profile.nicknameLabel")}
              </label>
              <input
                type="text"
                value={nickname}
                disabled={!isOwnProfile}
                onChange={(event) => setNickname(event.target.value)}
                maxLength={64}
                placeholder={t("profile.nicknamePlaceholder")}
                className="mt-2 w-full rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm text-white placeholder:text-slate-600 transition focus:border-limiar-500 focus:outline-none disabled:opacity-70"
              />
            </div>

            <div className="mt-6">
              <label className="text-[10px] font-bold uppercase tracking-[0.28em] text-slate-400">
                {t("profile.avatarLabel")}
              </label>
              <div className="mt-3 grid grid-cols-5 gap-3 sm:grid-cols-7">
                {PRESET_AVATARS.map((preset, idx) => {
                  const isSelected = avatarUrl === preset;
                  return (
                    <button
                      key={preset}
                      type="button"
                      disabled={!isOwnProfile}
                      onClick={() => setAvatarUrl(preset)}
                      style={{ animationDelay: `${idx * 35}ms`, animationFillMode: "both" }}
                      className={`animate-[landing-rise_0.35s_ease-out] aspect-square overflow-hidden rounded-2xl border-2 transition-all ${
                        isSelected ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.45)]" : "border-white/10 hover:border-white/30"
                      } disabled:cursor-default disabled:hover:border-white/10`}
                    >
                      <img src={preset} alt={`avatar ${idx + 1}`} className="h-full w-full object-cover" />
                    </button>
                  );
                })}
                <button
                  type="button"
                  disabled={!isOwnProfile || avatarUploading}
                  onClick={() => avatarInputRef.current?.click()}
                  className={`aspect-square overflow-hidden rounded-2xl border-2 border-dashed transition-all ${
                    avatarUrl && !PRESET_AVATARS.includes(avatarUrl) ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.45)]" : "border-white/15 hover:border-white/30"
                  } disabled:cursor-default disabled:opacity-60`}
                >
                  {avatarUrl && !PRESET_AVATARS.includes(avatarUrl) ? (
                    <ManagedImage src={avatarUrl} alt="upload" className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full w-full flex-col items-center justify-center gap-1 text-slate-400">
                      <span className="text-2xl">+</span>
                      <span className="text-[9px] font-bold uppercase tracking-[0.18em]">{t("profile.upload")}</span>
                    </div>
                  )}
                </button>
              </div>
              <input
                ref={avatarInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleAvatarUpload(file);
                  event.target.value = "";
                }}
              />
              {avatarUploadError ? <p className="mt-2 text-[11px] text-rose-400">{avatarUploadError}</p> : null}
            </div>
          </section>

          <section className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
              {t("profile.tokenEyebrow")}
            </p>
            <h2 className="mt-2 text-2xl font-bold text-white">{t("profile.tokenTitle")}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{t("profile.tokenDescription")}</p>

            <div className="mt-6 flex items-center justify-center">
              <div className="relative h-28 w-28">
                <div className="absolute inset-0 rounded-full blur-2xl opacity-50" style={{ background: previewColor }} />
                <div className="relative h-28 w-28 overflow-hidden rounded-full border-2 border-white/20" style={{ background: previewColor }}>
                  {tokenImageUrl ? <ManagedImage src={tokenImageUrl} alt="token" className="h-full w-full object-cover" /> : null}
                </div>
              </div>
            </div>

            <div className="mt-6 inline-flex w-full overflow-hidden rounded-2xl border border-white/10 text-[11px] font-bold uppercase tracking-[0.2em]">
              <button
                type="button"
                disabled={!isOwnProfile}
                onClick={() => setTokenTab("color")}
                className={`flex-1 py-2.5 transition-colors ${tokenTab === "color" ? "bg-white/10 text-white" : "text-slate-500 hover:bg-white/5"} disabled:cursor-default`}
              >
                {t("profile.tokenColorTab")}
              </button>
              <button
                type="button"
                disabled={!isOwnProfile}
                onClick={() => setTokenTab("image")}
                className={`flex-1 py-2.5 transition-colors ${tokenTab === "image" ? "bg-white/10 text-white" : "text-slate-500 hover:bg-white/5"} disabled:cursor-default`}
              >
                {t("profile.tokenImageTab")}
              </button>
            </div>

            <div className="mt-5">
              {tokenTab === "color" ? (
                <div className="grid grid-cols-8 gap-2.5">
                  {PRESET_COLORS.map((color) => (
                    <button
                      key={color}
                      type="button"
                      disabled={!isOwnProfile}
                      onClick={() => {
                        setTokenColor(color);
                        setTokenImageUrl(null);
                      }}
                      style={{ background: color }}
                      className={`aspect-square rounded-full border-2 transition-all ${tokenColor === color ? "border-white shadow-[0_0_20px_rgba(255,255,255,0.4)]" : "border-white/0 hover:border-white/40"} disabled:cursor-default`}
                    />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-4 gap-3 sm:grid-cols-6">
                  {PRESET_TOKENS.map((preset, idx) => {
                    const isSelected = tokenImageUrl === preset;
                    return (
                      <button
                        key={preset}
                        type="button"
                        disabled={!isOwnProfile}
                        onClick={() => setTokenImageUrl(preset)}
                        style={{ animationDelay: `${idx * 35}ms`, animationFillMode: "both" }}
                        className={`animate-[landing-rise_0.35s_ease-out] aspect-square overflow-hidden rounded-full border-2 transition-all ${isSelected ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.45)]" : "border-white/10 hover:border-white/30"} disabled:cursor-default`}
                      >
                        <img src={preset} alt={`token ${idx + 1}`} className="h-full w-full object-cover" />
                      </button>
                    );
                  })}
                  <button
                    type="button"
                    disabled={!isOwnProfile || tokenUploading}
                    onClick={() => tokenInputRef.current?.click()}
                    className={`aspect-square overflow-hidden rounded-full border-2 border-dashed transition-all ${tokenImageUrl && !PRESET_TOKENS.includes(tokenImageUrl) ? "border-limiar-400 shadow-[0_0_20px_rgba(167,139,250,0.45)]" : "border-white/15 hover:border-white/30"} disabled:cursor-default disabled:opacity-60`}
                  >
                    {tokenImageUrl && !PRESET_TOKENS.includes(tokenImageUrl) ? (
                      <ManagedImage src={tokenImageUrl} alt="upload" className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full w-full items-center justify-center text-2xl text-slate-400">+</div>
                    )}
                  </button>
                </div>
              )}
              <input
                ref={tokenInputRef}
                type="file"
                accept="image/png,image/jpeg,image/webp"
                className="hidden"
                onChange={(event) => {
                  const file = event.target.files?.[0];
                  if (file) void handleTokenUpload(file);
                  event.target.value = "";
                }}
              />
              {tokenUploadError ? <p className="mt-2 text-[11px] text-rose-400">{tokenUploadError}</p> : null}
            </div>
          </section>
        </div>

        <div className="space-y-6">
          <section className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
            <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">
              {t("profile.preferenceEyebrow")}
            </p>
            <h2 className="mt-2 text-2xl font-bold text-white">{t("profile.preferenceTitle")}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{t("profile.preferenceDescription")}</p>

            <div className="mt-6 space-y-3">
              {(["GM", "PLAYER"] as RoleMode[]).map((mode) => {
                const active = preferredMode === mode;
                return (
                  <button
                    key={mode}
                    type="button"
                    disabled={!isOwnProfile}
                    onClick={() => setPreferredMode(mode)}
                    className={`flex w-full items-center justify-between rounded-3xl border px-4 py-4 text-left transition ${
                      active
                        ? mode === "GM"
                          ? "border-amber-400/35 bg-amber-400/10 text-amber-100"
                          : "border-sky-400/35 bg-sky-400/10 text-sky-100"
                        : "border-white/8 bg-white/3 text-slate-200 hover:border-white/16 hover:bg-white/5"
                    } disabled:cursor-default`}
                  >
                    <div>
                      <p className="text-sm font-semibold text-white">
                        {mode === "GM" ? t("profile.preferenceGM") : t("profile.preferencePlayer")}
                      </p>
                      <p className="mt-1 text-xs text-slate-400">
                        {mode === "GM" ? t("profile.preferenceGMHint") : t("profile.preferencePlayerHint")}
                      </p>
                    </div>
                    {active ? <span className="text-lg">✓</span> : null}
                  </button>
                );
              })}
            </div>
          </section>

          {isOwnProfile ? (
            <section className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.82),rgba(2,6,23,0.94))] p-6">
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving}
                className="w-full rounded-full bg-gradient-to-r from-limiar-500 to-sky-500 px-5 py-3 text-sm font-bold uppercase tracking-[0.24em] text-white shadow-[0_0_24px_rgba(56,189,248,0.35)] transition hover:shadow-[0_0_32px_rgba(56,189,248,0.5)] disabled:opacity-60"
              >
                {saving ? t("profile.saving") : t("profile.save")}
              </button>
              {saveSuccess ? <p className="mt-3 text-sm text-emerald-300">{saveSuccess}</p> : null}
              {saveError ? <p className="mt-3 text-sm text-rose-300">{saveError}</p> : null}
            </section>
          ) : null}
        </div>
      </div>
    </section>
  );
};
