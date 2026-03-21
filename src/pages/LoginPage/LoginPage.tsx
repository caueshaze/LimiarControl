import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useForm } from "react-hook-form";
import { routes } from "../../app/routes/routes";
import { AuthField, AuthShell, AuthSubmitButton, useAuth } from "../../features/auth";
import { useLocale } from "../../shared/hooks/useLocale";

type LoginFormInputs = {
  username: string;
  pin: string;
};

const UserIcon = () => (
  <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.7}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6.75a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.5 19.5a7.5 7.5 0 0115 0" />
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

export const LoginPage = () => {
  const { login } = useAuth();
  const { locale, t } = useLocale();
  const navigate = useNavigate();
  const [loginError, setLoginError] = useState<string | null>(null);

  const copy =
    locale === "pt"
      ? {
          subtitle: "Acesse sua conta e volte para fichas, inventario e sessoes em andamento.",
          usernamePlaceholder: "Digite seu usuario",
          pinPlaceholder: "Digite seu PIN",
          footerPrompt: "Ainda nao tem conta?",
          requiredField: "Campo obrigatorio",
        }
      : {
          subtitle: "Access your account and jump back into sheets, inventory, and live sessions.",
          usernamePlaceholder: "Enter your username",
          pinPlaceholder: "Enter your PIN",
          footerPrompt: "Don't have an account yet?",
          requiredField: "This field is required",
        };

  const {
    register,
    handleSubmit,
    formState: { errors, isSubmitting },
  } = useForm<LoginFormInputs>();

  const onSubmit = async (data: LoginFormInputs) => {
    setLoginError(null);
    const profile = await login(data.username, data.pin);
    if (profile) {
      navigate(routes.home);
      return;
    }
    setLoginError(t("auth.loginError"));
  };

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
        type="password"
        label={t("auth.pin")}
        placeholder={copy.pinPlaceholder}
        icon={<LockIcon />}
        error={errors.pin ? copy.requiredField : null}
        autoComplete="current-password"
        {...register("pin", { required: true })}
      />

      {loginError ? (
        <div className="rounded-[20px] border border-rose-500/20 bg-rose-500/10 px-4 py-3 text-sm text-rose-200">
          {loginError}
        </div>
      ) : null}

      <AuthSubmitButton
        loading={isSubmitting}
        idleLabel={t("auth.loginSubmit")}
        loadingLabel={locale === "pt" ? "Entrando..." : "Signing in..."}
      />
    </form>
  );

  const footer = (
    <div className="text-center sm:text-left">
      <p className="text-sm text-slate-400">{copy.footerPrompt}</p>
      <Link
        to={routes.register}
        className="mt-1 inline-flex text-sm font-semibold text-limiar-200 transition-colors hover:text-white"
      >
        {t("auth.gotoRegister")}
      </Link>
    </div>
  );

  return (
    <AuthShell
      mode="login"
      title={t("auth.loginTitle")}
      subtitle={copy.subtitle}
      form={form}
      footer={footer}
    />
  );
};
