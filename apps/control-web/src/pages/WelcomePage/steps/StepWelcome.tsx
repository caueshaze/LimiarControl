import { useAuth } from "../../../features/auth";

type StepWelcomeProps = {
  onNext: () => void;
};

export const StepWelcome = ({ onNext }: StepWelcomeProps) => {
  const { user } = useAuth();
  const firstWord = (user?.displayName ?? user?.username ?? "viajante").split(" ")[0];

  return (
    <div className="text-center">
      <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-300">
        Bem-vindo
      </p>
      <h1 className="mt-3 font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
        Bem-vindo ao Limiar,
        <br />
        <span className="bg-gradient-to-r from-limiar-300 to-sky-300 bg-clip-text text-transparent">
          {firstWord}
        </span>
        .
      </h1>
      <p className="mx-auto mt-5 max-w-md text-sm leading-7 text-slate-300 sm:text-base">
        Vamos personalizar seu perfil em alguns passos rápidos. Você pode mudar tudo depois.
      </p>

      {/* Decorative pulsing ring */}
      <div className="relative mx-auto mt-10 h-32 w-32">
        <div className="absolute inset-0 rounded-full bg-limiar-500/20 blur-2xl motion-safe:animate-pulse" />
        <div className="absolute inset-2 rounded-full border border-limiar-400/40 motion-safe:animate-[landing-float_4s_ease-in-out_infinite]" />
        <div className="absolute inset-6 rounded-full border border-sky-300/30 motion-safe:animate-[landing-float_5s_ease-in-out_infinite_reverse]" />
        <div className="absolute inset-1/2 -translate-x-1/2 -translate-y-1/2">
          <div className="h-3 w-3 -translate-x-1/2 -translate-y-1/2 rounded-full bg-limiar-300 shadow-[0_0_24px_rgba(167,139,250,0.9)]" />
        </div>
      </div>

      <button
        type="button"
        onClick={onNext}
        className="mt-10 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-limiar-500 to-limiar-400 px-8 py-3.5 text-xs font-bold uppercase tracking-[0.28em] text-white shadow-[0_0_28px_rgba(139,92,246,0.45)] transition-all hover:shadow-[0_0_40px_rgba(139,92,246,0.65)] active:scale-95"
      >
        Vamos lá <span aria-hidden>→</span>
      </button>
    </div>
  );
};
