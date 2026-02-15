import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";

type LoginFormInputs = {
  username: string;
  pin: string;
};

export const LoginPage = () => {
  const { login } = useAuth();
  const { t } = useLocale();
  const navigate = useNavigate();
  const [loginError, setLoginError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormInputs>();

  const onSubmit = async (data: LoginFormInputs) => {
    setLoginError(null);
    const profile = await login(data.username, data.pin);
    if (profile) {
      navigate(profile.role === "GM" ? routes.gmHome : routes.playerHome);
    } else {
      setLoginError(t("auth.loginError"));
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Brand Header */}
        <div className="mb-8 text-center">
          <h1 className="bg-gradient-to-r from-limiar-300 to-limiar-500 bg-clip-text text-5xl font-extrabold text-transparent drop-shadow-sm">
            Limiar
          </h1>
          <p className="mt-2 text-sm font-medium uppercase tracking-[0.3em] text-limiar-200/60">
            System Control
          </p>
        </div>

        {/* Card */}
        <div className="overflow-hidden rounded-3xl border border-white/10 bg-white/5 p-1 backdrop-blur-xl shadow-2xl">
          <div className="rounded-[1.25rem] bg-void-950/80 p-8 shadow-inner border border-white/5">
            <h2 className="mb-6 text-xl font-semibold text-white">{t("auth.loginTitle")}</h2>

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
                    placeholder="Enter your username"
                  />
                </div>
                {errors.username && (
                  <p className="ml-1 text-xs text-rose-400">
                    {t("auth.username")} is required
                  </p>
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
                    {...register("pin", { required: true })}
                    className="relative block w-full rounded-xl border border-white/10 bg-void-900/50 px-4 py-3 text-sm text-slate-100 placeholder-slate-600 transition-colors focus:border-limiar-500 focus:bg-void-900 focus:outline-none focus:ring-1 focus:ring-limiar-500/50"
                    placeholder="Enter your PIN"
                  />
                </div>
                {errors.pin && (
                  <p className="ml-1 text-xs text-rose-400">
                    {t("auth.pin")} is required
                  </p>
                )}
              </div>

              {/* Error Message */}
              {loginError && (
                <div className="rounded-lg border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
                  {loginError}
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
                    t("auth.loginSubmit")
                  )}
                </span>
                <div className="absolute inset-0 -z-10 bg-gradient-to-r from-violet-600 to-indigo-600 opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
              </button>
            </form>
          </div>
        </div>

        {/* Footer Link */}
        <div className="mt-8 text-center">
          <Link
            to={routes.register}
            className="text-xs font-medium text-slate-400 transition-colors hover:text-limiar-300"
          >
            {t("auth.gotoRegister")}
          </Link>
        </div>
      </div>
    </div>
  );
};
