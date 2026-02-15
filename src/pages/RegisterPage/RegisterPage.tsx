import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";
import { http } from "../../shared/api/http";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";

type RegisterFormInputs = {
  username: string;
  pin: string;
  displayName: string;
  role: "GM" | "PLAYER";
};

export const RegisterPage = () => {
  const { register: registerUser } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const { toast, showToast, clearToast } = useToast();
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormInputs>({
    defaultValues: { role: "PLAYER" },
  });

  const onSubmit = async (data: RegisterFormInputs) => {
    setRegisterError(null);
    const profile = await registerUser(
      data.username,
      data.pin,
      data.displayName || undefined,
      data.role
    );
    if (profile) {
      navigate(profile.role === "GM" ? routes.gmHome : routes.playerHome);
    } else {
      setRegisterError(t("auth.registerError"));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <Toast toast={toast} onClose={clearToast} />
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="mb-8 text-center">
          <h1 className="bg-gradient-to-r from-limiar-300 to-limiar-500 bg-clip-text text-5xl font-extrabold text-transparent drop-shadow-sm">
            Limiar
          </h1>
          <p className="mt-2 text-sm font-medium uppercase tracking-[0.3em] text-limiar-200/60">
            Join the System
          </p>
        </div>

        {/* Card */}
        <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-1 backdrop-blur-xl shadow-2xl">
          <div className="rounded-[1.25rem] bg-void-950/80 p-8 shadow-inner border border-white/5">
            <h2 className="mb-6 text-xl font-semibold text-white">{t("auth.registerTitle")}</h2>

            <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
              {/* Username Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 ml-1">
                  {t("auth.username")}
                </label>
                <div className="relative group">
                  <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-limiar-500/20 to-purple-500/20 opacity-0 transition duration-500 group-focus-within:opacity-100" />
                  <input
                    {...register("username", { required: true })}
                    className="relative block w-full rounded-xl border border-white/10 bg-void-900/50 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 transition-colors focus:border-limiar-500 focus:bg-void-900 focus:outline-none focus:ring-1 focus:ring-limiar-500/50"
                    placeholder="Choose a username"
                  />
                </div>
                {errors.username && (
                  <p className="ml-1 text-xs text-rose-400">
                    {t("auth.username")} is required
                  </p>
                )}
              </div>

              {/* Display Name Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 ml-1">
                  {t("auth.displayName")}
                </label>
                <div className="relative group">
                  <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-limiar-500/20 to-purple-500/20 opacity-0 transition duration-500 group-focus-within:opacity-100" />
                  <input
                    {...register("displayName")}
                    className="relative block w-full rounded-xl border border-white/10 bg-void-900/50 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 transition-colors focus:border-limiar-500 focus:bg-void-900 focus:outline-none focus:ring-1 focus:ring-limiar-500/50"
                    placeholder="How should we call you?"
                  />
                </div>
              </div>

              {/* Role Selection */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 ml-1">
                  {t("auth.roleLabel")}
                </label>
                <div className="grid gap-3 sm:grid-cols-2">
                  {[
                    { value: "PLAYER", label: t("auth.rolePlayer"), description: t("auth.rolePlayerHint") },
                    { value: "GM", label: t("auth.roleGm"), description: t("auth.roleGmHint") },
                  ].map((option) => (
                    <label
                      key={option.value}
                      className="group flex cursor-pointer items-center gap-3 rounded-2xl border border-white/10 bg-void-900/40 px-4 py-3 text-sm text-slate-200 transition-colors hover:border-limiar-500/50"
                    >
                      <input
                        type="radio"
                        value={option.value}
                        className="h-4 w-4 accent-limiar-500"
                        {...register("role", { required: true })}
                      />
                      <div>
                        <p className="text-sm font-semibold text-white">{option.label}</p>
                        <p className="text-xs text-slate-400">{option.description}</p>
                      </div>
                    </label>
                  ))}
                </div>
                {errors.role && (
                  <p className="ml-1 text-xs text-rose-400">{t("auth.roleRequired")}</p>
                )}
              </div>

              {/* PIN Input */}
              <div className="space-y-1.5">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-400 ml-1">
                  {t("auth.pin")}
                </label>
                <div className="relative group">
                  <div className="absolute -inset-0.5 rounded-xl bg-gradient-to-r from-limiar-500/20 to-purple-500/20 opacity-0 transition duration-500 group-focus-within:opacity-100" />
                  <input
                    type="password"
                    {...register("pin", { required: true, minLength: 4 })}
                    className="relative block w-full rounded-xl border border-white/10 bg-void-900/50 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 transition-colors focus:border-limiar-500 focus:bg-void-900 focus:outline-none focus:ring-1 focus:ring-limiar-500/50"
                    placeholder="Create a secure PIN"
                  />
                </div>
                {errors.pin && (
                  <p className="ml-1 text-xs text-rose-400">
                    {errors.pin.type === "minLength" ? "PIN must be at least 4 characters" : `${t("auth.pin")} is required`}
                  </p>
                )}
              </div>

              {/* Error Message */}
              {registerError && (
                <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  {registerError}
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="group relative mt-2 w-full overflow-hidden rounded-xl bg-limiar-600 px-4 py-3.5 text-sm font-bold text-white shadow-[0_0_20px_rgba(124,58,237,0.3)] transition-all hover:bg-limiar-500 hover:shadow-[0_0_30px_rgba(139,92,246,0.5)] active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-70"
              >
                <span className="relative z-10 flex items-center justify-center gap-2">
                  {isSubmitting ? (
                    <svg
                      className="h-4 w-4 animate-spin text-white"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      ></circle>
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      ></path>
                    </svg>
                  ) : (
                    t("auth.registerSubmit")
                  )}
                </span>
                <div className="absolute inset-0 -z-10 bg-gradient-to-r from-violet-600 to-indigo-600 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              </button>
            </form>
          </div>
        </div>

        {/* Footer Link */}
        <div className="mt-8 space-y-4 text-center">
          <Link
            to={routes.login}
            className="text-xs font-medium text-slate-400 transition-colors hover:text-limiar-300"
          >
            {t("auth.gotoLogin")}
          </Link>
          {import.meta.env.DEV && (
            <div className="flex justify-center">
              <button
                type="button"
                onClick={async () => {
                  if (resetting) return;
                  setResetting(true);
                  try {
                    await http.post("/dev/reset", {});
                    showToast({
                      variant: "success",
                      title: t("auth.devResetSuccess"),
                      description: t("auth.devResetSuccessBody"),
                    });
                  } catch (error: { message?: string }) {
                    showToast({
                      variant: "error",
                      title: t("auth.devResetError"),
                      description: error?.message ?? t("auth.devResetErrorBody"),
                    });
                  } finally {
                    setResetting(false);
                  }
                }}
                className="rounded-full border border-rose-500/30 px-4 py-2 text-[10px] font-semibold uppercase tracking-[0.3em] text-rose-200 hover:border-rose-400 disabled:cursor-not-allowed disabled:opacity-60"
                disabled={resetting}
              >
                {resetting ? t("auth.devResetting") : t("auth.devReset")}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
