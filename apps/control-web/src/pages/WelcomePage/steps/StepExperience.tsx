import { useState } from "react";

type ExperienceMode = "GM" | "PLAYER";

type StepExperienceProps = {
  mode: ExperienceMode | null;
  onModeChange: (mode: ExperienceMode) => void;
  onBack: () => void;
  onFinish: () => void;
  submitting: boolean;
  submitError: string | null;
};

const OPTIONS = [
  {
    key: "GM" as const,
    title: "Mestre",
    tagline: "Conduza a mesa",
    description:
      "Narre histórias, crie mundos e conduza seus jogadores por encontros memoráveis. Como Mestre, você prepara campanhas, organiza mesas, controla criaturas, molda cenas e transforma decisões em consequências.",
    image: "/onboarding/Mestre.png",
    accentGlow: "rgba(251,191,36,0.35)",
    borderSelected: "border-amber-400/70",
    shadowSelected: "shadow-[0_0_48px_rgba(251,191,36,0.3),inset_0_0_0_1px_rgba(251,191,36,0.12)]",
    gradientOverlay: "from-amber-950/60 via-transparent to-transparent",
    badgeColor: "border-amber-400/40 bg-amber-400/10 text-amber-200",
  },
  {
    key: "PLAYER" as const,
    title: "Jogador",
    tagline: "Viva a aventura",
    description:
      "Viva a aventura pelo olhar do seu personagem. Como Jogador, você entra em mesas, acompanha sessões, evolui sua ficha, toma decisões perigosamente brilhantes e descobre até onde sua história pode chegar.",
    image: "/onboarding/Jogador.png",
    accentGlow: "rgba(56,189,248,0.35)",
    borderSelected: "border-sky-400/70",
    shadowSelected: "shadow-[0_0_48px_rgba(56,189,248,0.3),inset_0_0_0_1px_rgba(56,189,248,0.12)]",
    gradientOverlay: "from-sky-950/60 via-transparent to-transparent",
    badgeColor: "border-sky-400/40 bg-sky-400/10 text-sky-200",
  },
] as const;

export const StepExperience = ({
  mode,
  onModeChange,
  onBack,
  onFinish,
  submitting,
  submitError,
}: StepExperienceProps) => {
  const [hovered, setHovered] = useState<ExperienceMode | null>(null);

  return (
    <div>
      <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-300">
        Por onde você começa?
      </p>
      <h2 className="mt-2 font-display text-3xl font-bold text-white">
        Sua preferência inicial
      </h2>
      <p className="mt-2 text-sm text-slate-400">
        Você pode alternar livremente entre os dois modos depois — isso só define seu ponto de partida.
      </p>

      <div className="mt-6 grid gap-4 sm:grid-cols-2">
        {OPTIONS.map((option) => {
          const isSelected = mode === option.key;
          const isOtherSelected = mode !== null && mode !== option.key;

          return (
            <button
              key={option.key}
              type="button"
              onClick={() => onModeChange(option.key)}
              onMouseEnter={() => setHovered(option.key)}
              onMouseLeave={() => setHovered(null)}
              className={`group relative overflow-hidden rounded-[22px] border-2 text-left transition-all duration-300 ${
                isSelected
                  ? `${option.borderSelected} ${option.shadowSelected}`
                  : isOtherSelected
                    ? "border-white/8 opacity-55 hover:opacity-80"
                    : "border-white/12 hover:border-white/28"
              }`}
            >
              {/* Image */}
              <div className="relative h-52 overflow-hidden">
                <img
                  src={option.image}
                  alt={option.title}
                  className={`h-full w-full object-cover object-top transition-transform duration-700 ${
                    isSelected || hovered === option.key ? "scale-[1.06] translate-y-1" : "scale-100 translate-y-1"
                  }`}
                />
                {/* Gradient overlay top */}
                <div className={`absolute inset-0 bg-gradient-to-b ${option.gradientOverlay}`} />
                {/* Bottom fade for text */}
                <div className="absolute inset-0 bg-gradient-to-t from-[#070712] via-[#070712]/60 to-transparent" />

                {/* Badge top-left */}
                <div className="absolute left-3 top-3">
                  <span className={`rounded-full border px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.2em] ${option.badgeColor}`}>
                    {option.tagline}
                  </span>
                </div>

                {/* Checkmark top-right when selected */}
                {isSelected && (
                  <div className="absolute right-3 top-3 flex h-7 w-7 items-center justify-center rounded-full bg-white/20 backdrop-blur-sm">
                    <svg className="h-4 w-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                )}
              </div>

              {/* Content */}
              <div className="p-5">
                <h3 className="font-display text-xl font-bold text-white">{option.title}</h3>
                <p className="mt-2 text-xs leading-5 text-slate-400">{option.description}</p>
              </div>

              {/* Glow on selected */}
              {isSelected && (
                <div
                  aria-hidden
                  className="pointer-events-none absolute inset-0 rounded-[22px] opacity-20"
                  style={{
                    background: `radial-gradient(ellipse at 50% 0%, ${option.accentGlow}, transparent 70%)`,
                  }}
                />
              )}
            </button>
          );
        })}
      </div>

      {submitError && (
        <p className="mt-4 rounded-xl border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-300">
          {submitError}
        </p>
      )}

      <div className="mt-6 flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          disabled={submitting}
          className="rounded-full border border-white/10 bg-white/5 px-5 py-2.5 text-[11px] font-bold uppercase tracking-[0.24em] text-slate-300 transition hover:border-white/20 hover:text-white active:scale-95 disabled:opacity-40"
        >
          ← Voltar
        </button>
        <button
          type="button"
          onClick={onFinish}
          disabled={submitting || mode === null}
          className="rounded-full bg-gradient-to-r from-emerald-500 to-limiar-400 px-7 py-2.5 text-[11px] font-bold uppercase tracking-[0.24em] text-white shadow-[0_0_24px_rgba(16,185,129,0.45)] transition-all hover:shadow-[0_0_36px_rgba(16,185,129,0.65)] active:scale-95 disabled:opacity-40 disabled:shadow-none"
        >
          {submitting ? "Salvando..." : "Começar agora ✨"}
        </button>
      </div>
    </div>
  );
};
