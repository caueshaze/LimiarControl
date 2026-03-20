import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { routes } from "../../app/routes/routes";
import {
  AuthField,
  AuthShell,
  AuthSubmitButton,
  useAuth,
} from "../../features/auth";
import { http } from "../../shared/api/http";
import { useLocale } from "../../shared/hooks/useLocale";
import { useToast } from "../../shared/hooks/useToast";
import { Toast } from "../../shared/ui/Toast";

type RegisterFormInputs = {
  username: string;
  pin: string;
  displayName: string;
  role: "GM" | "PLAYER";
};

const UserIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6.75a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 19.5a7.5 7.5 0 0115 0" />
  </svg>
);

const SparkIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M12 3l1.9 5.6L19.5 10l-5.6 1.4L12 17l-1.9-5.6L4.5 10l5.6-1.4L12 3z" />
  </svg>
);

const LockIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7}>
    <path
      strokeLinecap="round"
      strokeLinejoin="round"
      d="M16.5 10.5V8.25a4.5 4.5 0 10-9 0v2.25m-1.5 0h12a1.5 1.5 0 011.5 1.5v6a1.5 1.5 0 01-1.5 1.5h-12A1.5 1.5 0 014.5 18v-6A1.5 1.5 0 016 10.5z"
    />
  </svg>
);

export const RegisterPage = () => {
  const { register: registerUser } = useAuth();
  const { locale, t } = useLocale();
  const navigate = useNavigate();
  const { toast, showToast, clearToast } = useToast();
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [resetting, setResetting] = useState(false);

  const copy =
    locale === "pt"
      ? {
          subtitle: "Crie sua conta, escolha seu perfil e entre na campanha com tudo pronto para jogar.",
          usernamePlaceholder: "Escolha seu usuario",
          displayNamePlaceholder: "Como voce quer aparecer para o grupo?",
          pinPlaceholder: "Crie um PIN seguro",
          requiredField: "Campo obrigatorio",
          pinTooShort: "PIN deve ter pelo menos 4 caracteres",
          roleHelper: "Escolha como voce quer entrar no ecossistema da mesa.",
          resetHint: "Ferramenta de desenvolvimento para limpar dados locais rapidamente.",
        }
      : {
          subtitle: "Create your account, choose your role, and enter the campaign ready to play.",
          usernamePlaceholder: "Choose your username",
          displayNamePlaceholder: "How should the party see you?",
          pinPlaceholder: "Create a secure PIN",
          requiredField: "This field is required",
          pinTooShort: "PIN must be at least 4 characters",
          roleHelper: "Choose how you want to enter the tabletop ecosystem.",
          resetHint: "Development tool to quickly clear local data.",
        };

  const {
    register,
    watch,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<RegisterFormInputs>({
    defaultValues: { role: "PLAYER" },
  });

  const selectedRole = watch("role");

  const onSubmit = async (data: RegisterFormInputs) => {
    setRegisterError(null);
    const profile = await registerUser(
      data.username,
      data.pin,
      data.displayName || undefined,
      data.role
    );
    if (profile) {
      navigate(routes.home);
      return;
    }
    setRegisterError(t("auth.registerError"));
  };

  const roleOptions = [
    {
      value: "PLAYER" as const,
      label: t("auth.rolePlayer"),
      description: t("auth.rolePlayerHint"),
      accent: "from-sky-400/18 via-sky-300/10 to-transparent",
    },
    {
      value: "GM" as const,
      label: t("auth.roleGm"),
      description: t("auth.roleGmHint"),
      accent: "from-amber-400/18 via-limiar-400/10 to-transparent",
    },
  ];

  const form = (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
      <AuthField
        label={t("auth.username")}
        placeholder={copy.usernamePlaceholder}
        icon={<UserIcon />}
        error={errors.username ? copy.requiredField : null}
        autoComplete="username"
        {...register("username", { required: true })}
      />

      <AuthField
        label={t("auth.displayName")}
        placeholder={copy.displayNamePlaceholder}
        icon={<SparkIcon />}
        autoComplete="nickname"
        {...register("displayName")}
      />

      <div className="space-y-2">
        <div className="flex items-center justify-between gap-3">
          <label className="ml-1 text-[11px] font-semibold uppercase tracking-[0.28em] text-slate-400">
            {t("auth.roleLabel")}
          </label>
          <p className="text-[11px] text-slate-500">{copy.roleHelper}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          {roleOptions.map((option, index) => {
            const isSelected = selectedRole === option.value;
            return (
              <label
                key={option.value}
                className={`group relative cursor-pointer overflow-hidden rounded-[24px] border p-4 transition duration-300 ${
                  isSelected
                    ? "border-limiar-300/25 bg-white/[0.06] shadow-[0_18px_40px_rgba(167,139,250,0.14)]"
                    : "border-white/10 bg-white/[0.03] hover:border-white/20"
                } motion-safe:animate-[landing-rise_0.75s_ease-out_both]`}
                style={{ animationDelay: `${index * 120}ms` }}
              >
                <div className={`absolute inset-0 bg-[linear-gradient(135deg,var(--tw-gradient-stops))] ${option.accent}`} />
                <div className="relative">
                  <div className="flex items-start gap-3">
                    <input
                      type="radio"
                      value={option.value}
                      className="mt-1 h-4 w-4 accent-limiar-400"
                      {...register("role", { required: true })}
                    />
                    <div>
                      <p className="text-sm font-semibold text-white">{option.label}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{option.description}</p>
                    </div>
                  </div>
                  <div className="mt-4 inline-flex rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-300">
                    {isSelected ? (locale === "pt" ? "Selecionado" : "Selected") : locale === "pt" ? "Disponivel" : "Available"}
                  </div>
                </div>
              </label>
            );
          })}
        </div>

        {errors.role ? <p className="ml-1 text-xs text-rose-300">{t("auth.roleRequired")}</p> : null}
      </div>

      <AuthField
        type="password"
        label={t("auth.pin")}
        placeholder={copy.pinPlaceholder}
        icon={<LockIcon />}
        error={
          errors.pin
            ? errors.pin.type === "minLength"
              ? copy.pinTooShort
              : copy.requiredField
            : null
        }
        autoComplete="new-password"
        {...register("pin", { required: true, minLength: 4 })}
      />

      {registerError ? (
        <div className="rounded-[20px] border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {registerError}
        </div>
      ) : null}

      <AuthSubmitButton
        loading={isSubmitting}
        idleLabel={t("auth.registerSubmit")}
        loadingLabel={locale === "pt" ? "Criando conta..." : "Creating account..."}
      />
    </form>
  );

  const footer = (
    <div className="space-y-4">
      <div className="text-center sm:text-left">
        <Link
          to={routes.login}
          className="inline-flex text-sm font-semibold text-limiar-200 transition-colors hover:text-white"
        >
          {t("auth.gotoLogin")}
        </Link>
      </div>

      {import.meta.env.DEV ? (
        <div className="flex flex-col gap-3 rounded-[24px] border border-rose-400/15 bg-rose-400/8 p-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-rose-100">
              {t("auth.devReset")}
            </p>
            <p className="mt-1 text-xs leading-6 text-rose-100/75">{copy.resetHint}</p>
          </div>
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
              } catch (error: any) {
                showToast({
                  variant: "error",
                  title: t("auth.devResetError"),
                  description: error?.message ?? t("auth.devResetErrorBody"),
                });
              } finally {
                setResetting(false);
              }
            }}
            className="rounded-full border border-rose-300/20 bg-rose-500/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-rose-100 transition-colors hover:border-rose-200/40 hover:bg-rose-500/16 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={resetting}
          >
            {resetting ? t("auth.devResetting") : t("auth.devReset")}
          </button>
        </div>
      ) : null}
    </div>
  );

  return (
    <>
      <Toast toast={toast} onClose={clearToast} />
      <AuthShell
        mode="register"
        title={t("auth.registerTitle")}
        subtitle={copy.subtitle}
        form={form}
        footer={footer}
      />
    </>
  );
};
