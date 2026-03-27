import { useLocale } from "../../../shared/hooks/useLocale";

type AuthMode = "login" | "register";

type ShowcaseContent = {
  badge: string;
  title: string;
  body: string;
  surfaceLabel: string;
  surfaceTitle: string;
  liveLabel: string;
  pulseLabel: string;
  pulseBody: string;
  modulesLabel: string;
  modules: string[];
  chips: string[];
  stats: Array<{ value: string; label: string }>;
  timeline: Array<{ label: string; status: string; tone: string }>;
};

const showcaseContent: Record<"pt" | "en", Record<AuthMode, ShowcaseContent>> = {
  pt: {
    login: {
      badge: "A mesa continua viva entre sessoes",
      title: "Entre e volte direto para a sua campanha.",
      body:
        "Retome fichas, inventario, board e comandos da mesa sem perder o ritmo da aventura.",
      surfaceLabel: "Superficie de comando",
      surfaceTitle: "Canal de acesso do Limiar",
      liveLabel: "Ao vivo",
      pulseLabel: "Pulso da sessao",
      pulseBody: "Feedback visual rapido para rolagens, estados e comandos.",
      modulesLabel: "Modulos conectados",
      modules: ["Ficha", "Loja", "Inventario", "Board", "NPCs"],
      chips: ["Board sincronizado", "Inventario em contexto", "Sessao ao vivo"],
      stats: [
        { value: "RT", label: "Sync da mesa" },
        { value: "24/7", label: "Campanha persistente" },
        { value: "GM", label: "Comando em foco" },
      ],
      timeline: [
        { label: "Ficha carregada", status: "Pronta", tone: "text-emerald-200 bg-emerald-400/10 border-emerald-300/15" },
        { label: "Board do grupo", status: "Ao vivo", tone: "text-sky-100 bg-sky-400/10 border-sky-300/15" },
        { label: "Loja da sessao", status: "Em espera", tone: "text-amber-100 bg-amber-400/10 border-amber-300/15" },
      ],
    },
    register: {
      badge: "Crie sua conta e escolha seu papel na mesa",
      title: "Prepare sua entrada na campanha em poucos passos.",
      body:
        "Escolha se voce entra como jogador ou mestre e comece com tudo pronto para acompanhar a aventura.",
      surfaceLabel: "Superficie de comando",
      surfaceTitle: "Canal de acesso do Limiar",
      liveLabel: "Ao vivo",
      pulseLabel: "Pulso da sessao",
      pulseBody: "Feedback visual rapido para rolagens, estados e comandos.",
      modulesLabel: "Modulos conectados",
      modules: ["Ficha", "Loja", "Inventario", "Board", "NPCs"],
      chips: ["Perfil de jogador", "Perfil de mestre", "Fluxo guiado"],
      stats: [
        { value: "01", label: "Conta unica" },
        { value: "2x", label: "Perfis bem definidos" },
        { value: "+", label: "Modulos conectados" },
      ],
      timeline: [
        { label: "Perfil escolhido", status: "Jogador ou GM", tone: "text-limiar-100 bg-limiar-400/10 border-limiar-300/15" },
        { label: "Entrada pronta", status: "Sem friccao", tone: "text-emerald-200 bg-emerald-400/10 border-emerald-300/15" },
        { label: "Proxima etapa", status: "Home ou campanha", tone: "text-sky-100 bg-sky-400/10 border-sky-300/15" },
      ],
    },
  },
  en: {
    login: {
      badge: "The table stays alive between sessions",
      title: "Sign in and jump straight back into your campaign.",
      body:
        "Return to character sheets, inventory, board updates, and live table commands without losing the adventure's momentum.",
      surfaceLabel: "Command surface",
      surfaceTitle: "Limiar access channel",
      liveLabel: "Live",
      pulseLabel: "Session pulse",
      pulseBody: "Fast visual feedback for rolls, states, and table commands.",
      modulesLabel: "Connected modules",
      modules: ["Sheet", "Shop", "Inventory", "Board", "NPCs"],
      chips: ["Synced board", "Contextual inventory", "Live session"],
      stats: [
        { value: "RT", label: "Table sync" },
        { value: "24/7", label: "Persistent campaign" },
        { value: "GM", label: "Control in focus" },
      ],
      timeline: [
        { label: "Character sheet", status: "Ready", tone: "text-emerald-200 bg-emerald-400/10 border-emerald-300/15" },
        { label: "Party board", status: "Live", tone: "text-sky-100 bg-sky-400/10 border-sky-300/15" },
        { label: "Session shop", status: "Waiting", tone: "text-amber-100 bg-amber-400/10 border-amber-300/15" },
      ],
    },
    register: {
      badge: "Create your account and choose your role at the table",
      title: "Get ready to enter the campaign in just a few steps.",
      body:
        "Choose whether you join as a player or GM and start with everything in place to follow the adventure.",
      surfaceLabel: "Command surface",
      surfaceTitle: "Limiar access channel",
      liveLabel: "Live",
      pulseLabel: "Session pulse",
      pulseBody: "Fast visual feedback for rolls, states, and table commands.",
      modulesLabel: "Connected modules",
      modules: ["Sheet", "Shop", "Inventory", "Board", "NPCs"],
      chips: ["Player flow", "GM flow", "Guided setup"],
      stats: [
        { value: "01", label: "Single account" },
        { value: "2x", label: "Clear roles" },
        { value: "+", label: "Connected modules" },
      ],
      timeline: [
        { label: "Role selected", status: "Player or GM", tone: "text-limiar-100 bg-limiar-400/10 border-limiar-300/15" },
        { label: "Entry flow", status: "Low friction", tone: "text-emerald-200 bg-emerald-400/10 border-emerald-300/15" },
        { label: "Next step", status: "Home or campaign", tone: "text-sky-100 bg-sky-400/10 border-sky-300/15" },
      ],
    },
  },
};

export const AuthShowcase = ({ mode }: { mode: AuthMode }) => {
  const { locale } = useLocale();
  const content = showcaseContent[locale][mode];

  return (
    <section className="relative h-full overflow-hidden rounded-[36px] border border-white/10 bg-[linear-gradient(180deg,rgba(9,11,28,0.92),rgba(3,7,18,0.96))] p-6 shadow-[0_30px_120px_rgba(2,6,23,0.5)] sm:p-8">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(167,139,250,0.2),transparent_34%),radial-gradient(circle_at_80%_15%,rgba(103,232,249,0.16),transparent_24%),radial-gradient(circle_at_40%_100%,rgba(251,191,36,0.1),transparent_24%)]" />
      <div className="absolute inset-0 opacity-[0.18] bg-[linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-size-[22px_22px]" />
      <div className="absolute -right-10 top-16 h-32 w-32 rounded-full bg-sky-400/20 blur-3xl motion-safe:animate-[auth-orbit_18s_linear_infinite]" />
      <div className="absolute -left-10 bottom-10 h-36 w-36 rounded-full bg-limiar-500/20 blur-3xl motion-safe:animate-[landing-float_10s_ease-in-out_infinite]" />

      <div className="relative">
        <div className="inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/5 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-slate-200">
          <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_14px_rgba(110,231,183,0.85)]" />
          {content.badge}
        </div>

        <h2 className="mt-6 max-w-2xl font-display text-4xl font-bold leading-tight text-white sm:text-5xl">
          {content.title}
        </h2>
        <p className="mt-4 max-w-2xl text-base leading-7 text-slate-300">{content.body}</p>

        <div className="mt-6 flex flex-wrap gap-2">
          {content.chips.map((chip) => (
            <span
              key={chip}
              className="rounded-full border border-white/10 bg-black/20 px-3 py-1.5 text-xs font-semibold text-slate-200 backdrop-blur-xl"
            >
              {chip}
            </span>
          ))}
        </div>

        <div className="mt-8 grid gap-4 sm:grid-cols-3">
          {content.stats.map((stat, index) => (
            <div
              key={stat.label}
              className="rounded-[24px] border border-white/10 bg-white/4 p-4 backdrop-blur-xl motion-safe:animate-[landing-rise_0.75s_ease-out_both]"
              style={{ animationDelay: `${index * 140}ms` }}
            >
              <p className="font-display text-3xl font-bold text-white">{stat.value}</p>
              <p className="mt-2 text-[11px] font-semibold uppercase tracking-[0.24em] text-slate-400">{stat.label}</p>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-4 lg:grid-cols-[1.08fr_0.92fr]">
            <div className="overflow-hidden rounded-[30px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.88),rgba(2,6,23,0.96))] p-5 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-slate-500">{content.surfaceLabel}</p>
                  <h3 className="mt-2 text-lg font-semibold text-white">{content.surfaceTitle}</h3>
                </div>
                <span className="rounded-full border border-emerald-300/15 bg-emerald-400/10 px-3 py-1 text-[11px] font-semibold text-emerald-200">
                  {content.liveLabel}
                </span>
              </div>

            <div className="mt-5 grid grid-cols-6 gap-2 rounded-[24px] border border-white/8 bg-black/20 p-3">
              {Array.from({ length: 18 }, (_, index) => {
                const active = [2, 3, 7, 8, 13].includes(index);
                const glowing = [10, 11, 16].includes(index);
                return (
                  <div
                    key={index}
                    className={`aspect-square rounded-xl border ${
                      active
                        ? "border-limiar-300/30 bg-limiar-400/18"
                        : glowing
                          ? "border-sky-300/30 bg-sky-400/14"
                          : "border-white/6 bg-white/3"
                    } ${active || glowing ? "motion-safe:animate-[landing-pulse_4.8s_ease-in-out_infinite]" : ""}`}
                    style={{ animationDelay: `${index * 100}ms` }}
                  />
                );
              })}
            </div>

            <div className="mt-5 space-y-3">
              {content.timeline.map((item, index) => (
                <div
                  key={item.label}
                  className="flex items-center justify-between rounded-[20px] border border-white/8 bg-white/3 px-4 py-3 motion-safe:animate-[landing-rise_0.75s_ease-out_both]"
                  style={{ animationDelay: `${index * 160 + 180}ms` }}
                >
                  <span className="text-sm text-slate-200">{item.label}</span>
                  <span className={`rounded-full border px-3 py-1 text-xs font-semibold ${item.tone}`}>
                    {item.status}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.7),rgba(2,6,23,0.92))] p-5">
              <p className="text-[10px] font-bold uppercase tracking-[0.26em] text-slate-500">{content.pulseLabel}</p>
              <div className="mt-4 flex items-center gap-4">
                <div className="flex h-20 w-20 items-center justify-center rounded-[24px] border border-white/10 bg-black/20 font-display text-3xl text-white motion-safe:animate-[landing-float_6.5s_ease-in-out_infinite]">
                  d20
                </div>
                <div className="space-y-2">
                  <div className="relative h-2.5 w-28 overflow-hidden rounded-full bg-slate-800">
                    <div className="absolute inset-y-0 left-0 w-4/5 rounded-full bg-[linear-gradient(90deg,#67e8f9,#c4b5fd)]" />
                    <div className="absolute inset-y-0 left-[-40%] w-10 rounded-full bg-white/35 blur-[5px] motion-safe:animate-[auth-sheen_3.6s_linear_infinite]" />
                  </div>
                  <p className="text-sm text-slate-300">{content.pulseBody}</p>
                </div>
              </div>
            </div>

            <div className="rounded-[28px] border border-white/10 bg-white/4 p-5 backdrop-blur-xl">
              <p className="text-[10px] font-bold uppercase tracking-[0.26em] text-slate-500">{content.modulesLabel}</p>
              <div className="mt-4 flex flex-wrap gap-2">
                {content.modules.map((item) => (
                  <span
                    key={item}
                    className="rounded-full border border-white/8 bg-black/20 px-3 py-1.5 text-xs font-semibold text-slate-200"
                  >
                    {item}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
