const playerBadges = [
  {
    name: "Lyra",
    tone: "border-sky-300/20 bg-sky-400/12 text-sky-100",
    badge: "Pronta",
    meta: "Sheet synced",
  },
  {
    name: "Kael",
    tone: "border-emerald-300/20 bg-emerald-400/12 text-emerald-100",
    badge: "Sincronizado",
    meta: "Sheet synced",
  },
  {
    name: "Mira",
    tone: "border-amber-300/20 bg-amber-400/12 text-amber-100",
    badge: "Em jogo",
    meta: "Sheet synced",
  },
] as const;

const commandCards = [
  {
    title: "Loja aberta",
    body: "Descanso curto liberado.",
    tone: "border-sky-300/20 bg-sky-400/10 text-sky-100",
    dot: "bg-sky-300",
  },
  {
    title: "Teste coletivo",
    body: "Percepcao para toda a party.",
    tone: "border-amber-300/20 bg-amber-400/10 text-amber-100",
    dot: "bg-amber-300",
  },
] as const;

const flowItems = [
  {
    label: "Inventario",
    hint: "Mudancas salvas",
    status: "Atualizado",
    tone: "border-emerald-300/20 bg-emerald-400/10 text-emerald-100",
  },
  {
    label: "Ficha",
    hint: "Pronta para entrar",
    status: "Pronta",
    tone: "border-limiar-300/20 bg-limiar-400/10 text-limiar-100",
  },
] as const;

const modules = ["Ficha", "Loja", "Inventario", "NPCs", "Dashboard", "Board"] as const;

export const LandingHeroVisual = () => (
  <div className="relative mx-auto w-full max-w-[40.5rem]">
    <div className="absolute -left-12 top-6 h-32 w-32 rounded-full bg-cyan-400/20 blur-3xl" />
    <div className="absolute -right-6 bottom-0 h-48 w-48 rounded-full bg-limiar-500/20 blur-3xl" />

    <div className="relative overflow-hidden rounded-[32px] border border-white/10 bg-[linear-gradient(180deg,rgba(15,23,42,0.94),rgba(3,7,18,0.98))] shadow-[0_30px_120px_rgba(2,6,23,0.6)]">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(139,92,246,0.18),transparent_34%),radial-gradient(circle_at_80%_20%,rgba(56,189,248,0.14),transparent_24%),linear-gradient(135deg,rgba(255,255,255,0.05),transparent_42%)]" />
      <div className="absolute inset-0 opacity-20 bg-[linear-gradient(rgba(255,255,255,0.08)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.08)_1px,transparent_1px)] bg-size-[24px_24px]" />

      <div className="relative space-y-5 p-5 md:p-6">
        <div className="flex flex-col gap-3 rounded-[24px] border border-white/8 bg-black/20 px-4 py-3 backdrop-blur-xl sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-[0.28em] text-limiar-300">Sessao ao vivo</p>
            <h3 className="mt-2 font-display text-xl text-white">A Fortaleza Partida</h3>
          </div>
          <div className="inline-flex items-center self-start rounded-full border border-emerald-300/20 bg-emerald-400/10 px-3 py-1 text-[11px] font-semibold text-emerald-200 sm:self-auto">
            3 players synced
          </div>
        </div>

        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,1.08fr)_minmax(0,0.92fr)]">
          <div className="space-y-4">
            <div className="overflow-hidden rounded-[28px] border border-white/8 bg-slate-950/80 p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]">
              <div className="mb-3 flex items-center justify-between gap-3">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Battle board</p>
                <span className="text-xs text-slate-400">Fog of war active</span>
              </div>
              <div className="grid grid-cols-6 gap-2 rounded-[22px] border border-white/6 bg-[linear-gradient(180deg,rgba(15,23,42,0.95),rgba(2,6,23,0.88))] p-3">
                {Array.from({ length: 24 }, (_, index) => {
                  const highlighted = [3, 4, 9, 15, 16, 21].includes(index);
                  const fogged = [1, 2, 7, 8, 13, 14].includes(index);
                  return (
                    <div
                      key={index}
                      className={`aspect-square rounded-xl border ${
                        highlighted
                          ? "border-limiar-400/40 bg-limiar-400/18"
                          : fogged
                            ? "border-slate-800 bg-slate-900"
                            : "border-white/6 bg-white/3"
                      } ${highlighted ? "motion-safe:animate-[landing-pulse_4.5s_ease-in-out_infinite]" : ""}`}
                    />
                  );
                })}
              </div>
            </div>

            <div className="space-y-4">
              <div className="rounded-[26px] border border-white/8 bg-white/3 p-4 backdrop-blur-xl">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Comandos</p>
                <div className="mt-4 space-y-3">
                  {commandCards.map((card) => (
                    <div
                      key={card.title}
                      className={`rounded-[20px] border px-4 py-3 ${card.tone}`}
                    >
                      <div className="flex items-start gap-3">
                        <span className={`mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full ${card.dot} shadow-[0_0_12px_currentColor]`} />
                        <div>
                          <p className="text-sm font-semibold">{card.title}</p>
                          <p className="mt-1 text-sm leading-5 text-white/75">{card.body}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[26px] border border-white/8 bg-white/3 p-4 backdrop-blur-xl">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Fluxo</p>
                <div className="mt-4 space-y-3">
                  {flowItems.map((item) => (
                    <div
                      key={item.label}
                      className="rounded-[18px] border border-white/8 bg-black/20 px-4 py-3"
                    >
                      <div className="space-y-2">
                        <p className="text-sm font-medium text-slate-100">{item.label}</p>
                        <p className="text-xs text-slate-500">{item.hint}</p>
                        <span
                          className={`inline-flex w-fit rounded-full border px-3 py-1 text-[11px] font-semibold ${item.tone}`}
                        >
                          {item.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-[24px] border border-white/8 bg-[linear-gradient(180deg,rgba(8,12,30,0.92),rgba(4,7,20,0.96))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                <div className="flex items-start gap-3">
                  <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl border border-limiar-300/15 bg-limiar-400/10 text-limiar-100">
                    <span className="font-display text-sm font-bold">GM</span>
                  </div>
                  <div>
                    <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Nota do mestre</p>
                    <p className="mt-2 text-sm leading-6 text-slate-200">
                      A pista sobre o reliquario aparece so depois da negociacao com o guardiao.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.95),rgba(6,10,24,0.95))] p-4 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
              <div className="flex items-center justify-between">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Party status</p>
                <span className="rounded-full bg-limiar-400/10 px-2 py-1 text-[10px] font-semibold text-limiar-200">
                  Act 2
                </span>
              </div>
              <div className="mt-4 space-y-3">
                {playerBadges.map((player) => (
                  <div
                    key={player.name}
                    className={`rounded-[20px] border px-4 py-3 ${player.tone}`}
                  >
                    <div className="space-y-2">
                      <div className="flex items-center justify-between gap-3">
                        <p className="text-base font-semibold">{player.name}</p>
                        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-white/80">
                          {player.badge}
                        </span>
                      </div>
                      <p className="text-[11px] uppercase tracking-[0.2em] text-white/55">
                        {player.meta}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="rounded-[28px] border border-white/8 bg-[linear-gradient(180deg,rgba(23,37,84,0.9),rgba(15,23,42,0.9))] p-4">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-400">Dice moment</p>
              <div className="mt-4 grid gap-4 xl:grid-cols-[auto_minmax(0,1fr)] xl:items-center">
                <div className="flex h-20 w-20 items-center justify-center rounded-[22px] border border-white/10 bg-black/20 font-display text-3xl text-white motion-safe:animate-[landing-float_6s_ease-in-out_infinite]">
                  d20
                </div>
                <div>
                  <p className="text-sm leading-6 text-slate-200">
                    Rolagens com feedback visual rapido e leitura imediata na mesa.
                  </p>
                  <p className="mt-2 text-lg font-semibold text-emerald-200">Critico: 20</p>
                </div>
              </div>
            </div>

            <div className="rounded-[28px] border border-white/8 bg-white/3 p-4 backdrop-blur-xl">
              <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Modulos conectados</p>
              <div className="mt-4 grid grid-cols-2 gap-2">
                {modules.map((label) => (
                  <div
                    key={label}
                    className="rounded-[18px] border border-white/8 bg-black/20 px-3 py-3 text-sm font-semibold text-slate-200"
                  >
                    {label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
);
