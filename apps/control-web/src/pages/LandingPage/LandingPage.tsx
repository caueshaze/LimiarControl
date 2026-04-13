import { Link } from "react-router-dom";
import { APP_NAME } from "../../app/config/appConfig";
import { routes } from "../../app/routes/routes";
import { useAuth } from "../../features/auth";
import { BrandMark } from "../../shared/ui";
import { LandingHeroVisual } from "./LandingHeroVisual";
import {
  landingEntryPoints,
  landingFeatureCards,
  landingSpotlights,
  landingStats,
  landingWorkflow,
} from "./landingContent";

export const LandingPage = () => {
  const { user } = useAuth();
  const currentYear = new Date().getFullYear();

  return (
    <div className="min-h-screen overflow-x-hidden bg-void-950 text-slate-100 selection:bg-limiar-400/30 selection:text-white">
      <div className="pointer-events-none fixed inset-0 overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(167,139,250,0.16),transparent_28%),radial-gradient(circle_at_15%_25%,rgba(34,211,238,0.14),transparent_18%),radial-gradient(circle_at_85%_18%,rgba(251,191,36,0.08),transparent_18%),linear-gradient(180deg,#050208_0%,#090413_35%,#050208_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(rgba(255,255,255,0.22)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.22)_1px,transparent_1px)] bg-size-[72px_72px] opacity-[0.07]" />
        <div className="absolute -left-24 top-16 h-72 w-72 rounded-full bg-limiar-500/20 blur-[140px] motion-safe:animate-[landing-drift_16s_ease-in-out_infinite]" />
        <div className="absolute right-0 top-0 h-128 w-lg rounded-full bg-sky-500/10 blur-[160px] motion-safe:animate-[landing-drift_18s_ease-in-out_infinite_reverse]" />
        <div className="absolute -bottom-32 left-1/3 h-72 w-72 rounded-full bg-emerald-400/10 blur-[150px] motion-safe:animate-[landing-float_14s_ease-in-out_infinite]" />
      </div>

      <header className="relative z-10 border-b border-white/6 bg-slate-950/50 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-5">
          <div className="flex items-center gap-4">
            <BrandMark size="md" />
            <div>
              <p className="font-display text-xl font-bold tracking-tight text-white">{APP_NAME}</p>
              <p className="text-xs uppercase tracking-[0.28em] text-slate-500">Mesa digital para campanhas conectadas</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {user ? (
              <Link
                to={routes.home}
                className="rounded-full border border-limiar-300/20 bg-limiar-400 px-5 py-2.5 text-sm font-bold text-slate-950 shadow-[0_0_28px_rgba(167,139,250,0.32)] transition-transform hover:scale-[1.02] hover:bg-limiar-300"
              >
                Abrir painel
              </Link>
            ) : (
              <>
                <Link
                  to={routes.login}
                  className="hidden text-sm font-semibold text-slate-300 transition-colors hover:text-white sm:block"
                >
                  Entrar
                </Link>
                <Link
                  to={routes.register}
                  className="rounded-full border border-white/10 bg-white/5 px-5 py-2.5 text-sm font-bold text-white transition-colors hover:border-limiar-300/20 hover:bg-limiar-400/12"
                >
                  Criar conta
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="relative z-10">
        <section className="mx-auto max-w-7xl px-6 pb-20 pt-16 lg:pb-24 lg:pt-24">
          <div className="grid items-center gap-14 lg:grid-cols-[minmax(0,0.92fr)_minmax(0,1.08fr)]">
            <div>
              <div className="inline-flex items-center gap-2 rounded-full border border-limiar-300/20 bg-limiar-400/10 px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-100">
                <span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_12px_rgba(110,231,183,0.8)]" />
                Campanha, ficha e sessao em um lugar
              </div>

              <h1 className="mt-8 max-w-3xl font-display text-5xl font-bold leading-[0.94] text-white sm:text-6xl lg:text-7xl">
                Sua campanha ganha um hub com
                <span className="bg-[linear-gradient(120deg,#c4b5fd_0%,#67e8f9_48%,#fde68a_100%)] bg-clip-text text-transparent"> cara de mesa viva.</span>
              </h1>

              <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
                O LimiarControl organiza o caos bom de uma campanha: ficha, loja, inventario, comandos do mestre, board e
                rolagens em uma experiencia com mais presenca visual e menos cara de painel vazio.
              </p>

              <div className="mt-10 flex flex-col gap-4 sm:flex-row">
                <Link
                  to={user ? routes.home : routes.register}
                  className="inline-flex items-center justify-center gap-2 rounded-2xl bg-limiar-400 px-7 py-4 text-base font-bold text-slate-950 shadow-[0_18px_40px_rgba(167,139,250,0.25)] transition-all hover:-translate-y-px hover:bg-limiar-300"
                >
                  {user ? "Entrar no painel" : "Comecar gratis"}
                  <ArrowIcon className="h-5 w-5" />
                </Link>
                {!user && (
                  <Link
                    to={routes.login}
                    className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/4 px-7 py-4 text-base font-semibold text-white transition-colors hover:border-white/20 hover:bg-white/8"
                  >
                    Ja tenho uma conta
                  </Link>
                )}
              </div>

              <div className="mt-8 grid gap-3 md:grid-cols-3">
                {landingEntryPoints.map((entry, index) => (
                  <div
                    key={entry.title}
                    className="group relative overflow-hidden rounded-3xl border border-white/8 bg-white/4 p-4 backdrop-blur-xl motion-safe:animate-[landing-rise_0.8s_ease-out_both]"
                    style={{ animationDelay: `${index * 140}ms` }}
                  >
                    <div className={`absolute inset-0 bg-[linear-gradient(135deg,var(--tw-gradient-stops))] ${entry.tone}`} />
                    <div className="relative">
                      <p className="text-sm font-semibold text-white">{entry.title}</p>
                      <p className="mt-2 text-sm leading-6 text-slate-300">{entry.body}</p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                {landingSpotlights.map((spotlight, index) => (
                  <div
                    key={spotlight.title}
                    className="rounded-3xl border border-white/8 bg-white/4 p-4 backdrop-blur-xl motion-safe:animate-[landing-rise_0.8s_ease-out_both]"
                    style={{ animationDelay: `${index * 140 + 220}ms` }}
                  >
                    <p className="text-sm font-semibold text-white">{spotlight.title}</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">{spotlight.body}</p>
                  </div>
                ))}
              </div>
            </div>

            <div className="motion-safe:animate-[landing-rise_1s_ease-out]">
              <LandingHeroVisual />
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 pb-20">
          <div className="grid gap-4 lg:grid-cols-4">
            {landingStats.map((stat, index) => (
              <div
                key={stat.label}
                className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.78),rgba(2,6,23,0.94))] p-6 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)] transition-transform duration-300 hover:-translate-y-0.5 motion-safe:animate-[landing-rise_0.8s_ease-out_both]"
                style={{ animationDelay: `${index * 120}ms` }}
              >
                <p className="text-3xl font-display font-bold text-white">{stat.value}</p>
                <p className="mt-3 text-sm font-semibold uppercase tracking-[0.22em] text-limiar-200">{stat.label}</p>
                <p className="mt-3 text-sm leading-6 text-slate-400">{stat.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 pb-20">
          <div className="mb-10 max-w-2xl">
            <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-sky-200">Tudo no mesmo fluxo</p>
            <h2 className="mt-4 font-display text-4xl font-bold text-white sm:text-5xl">
              Tudo o que a mesa precisa, sem quebrar o clima.
            </h2>
            <p className="mt-4 text-base leading-7 text-slate-400">
              Campanhas, fichas, loja, inventario e comandos convivem no mesmo fluxo para mestre e jogadores.
            </p>
          </div>

          <div className="grid gap-5 md:grid-cols-2">
            {landingFeatureCards.map((feature, index) => (
              <article
                key={feature.title}
                className="group relative overflow-hidden rounded-4xl border border-white/8 bg-[linear-gradient(180deg,rgba(15,23,42,0.85),rgba(2,6,23,0.92))] p-7 shadow-[0_24px_70px_rgba(2,6,23,0.28)] transition-transform hover:-translate-y-0.5 motion-safe:animate-[landing-rise_0.8s_ease-out_both]"
                style={{ animationDelay: `${index * 140}ms` }}
              >
                <div className={`absolute inset-0 bg-[radial-gradient(circle_at_top_left,rgba(255,255,255,0.04),transparent_28%),linear-gradient(135deg,var(--tw-gradient-stops))] ${feature.accent}`} />
                <div className="relative">
                  <div className="flex h-14 w-14 items-center justify-center rounded-2xl border border-white/10 bg-white/4 text-limiar-100 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]">
                    <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                      <path strokeLinecap="round" strokeLinejoin="round" d={feature.iconPath} />
                    </svg>
                  </div>
                  <h3 className="mt-6 text-2xl font-bold text-white">{feature.title}</h3>
                  <p className="mt-3 max-w-xl text-sm leading-7 text-slate-300">{feature.description}</p>
                </div>
              </article>
            ))}
          </div>
        </section>

        <section className="mx-auto max-w-7xl px-6 pb-24">
          <div className="grid gap-8 lg:grid-cols-[minmax(0,0.88fr)_minmax(0,1.12fr)]">
            <div className="rounded-[34px] border border-white/8 bg-[linear-gradient(180deg,rgba(9,11,28,0.9),rgba(3,7,18,0.95))] p-8">
              <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-amber-200">Fluxo da experiencia</p>
              <h2 className="mt-4 font-display text-4xl font-bold text-white">Do preparo ao play sem trocar de clima.</h2>
              <div className="mt-8 space-y-6">
                {landingWorkflow.map((item, index) => (
                  <div
                    key={item.step}
                    className="flex gap-4 motion-safe:animate-[landing-rise_0.8s_ease-out_both]"
                    style={{ animationDelay: `${index * 140}ms` }}
                  >
                    <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl border border-white/10 bg-white/4 font-display text-lg font-bold text-white">
                      {item.step}
                    </div>
                    <div>
                      <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                      <p className="mt-2 text-sm leading-7 text-slate-400">{item.description}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="grid gap-5 md:grid-cols-2">
              <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(17,24,39,0.84),rgba(2,6,23,0.92))] p-6">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">Player board</p>
                <div className="mt-5 space-y-4">
                  <div className="rounded-3xl border border-white/8 bg-white/3 p-4">
                    <p className="text-sm font-semibold text-white">Ficha pronta para sessao</p>
                    <p className="mt-2 text-sm leading-6 text-slate-400">Criacao, equipamento inicial e continuidade visual com inventario e play sheet.</p>
                  </div>
                  <div className="rounded-3xl border border-emerald-300/15 bg-emerald-400/10 p-4">
                    <p className="text-sm font-semibold text-emerald-100">Loja liberada pelo mestre</p>
                    <p className="mt-2 text-sm leading-6 text-emerald-50/80">A experiencia fica mais crivel quando a interface mostra o momento do jogo, nao so uma lista de links.</p>
                  </div>
                </div>
              </div>

              <div className="rounded-[30px] border border-white/8 bg-[linear-gradient(180deg,rgba(24,24,27,0.82),rgba(3,7,18,0.94))] p-6">
                <p className="text-[10px] font-bold uppercase tracking-[0.24em] text-slate-500">GM dashboard</p>
                <div className="mt-5 space-y-3">
                  {["Campanhas ativas", "Catalogo da loja", "Inventario por party", "Sessoes em andamento"].map((label) => (
                    <div key={label} className="flex items-center justify-between rounded-2xl border border-white/8 bg-white/3 px-4 py-3">
                      <span className="text-sm text-slate-200">{label}</span>
                      <span className="text-xs font-semibold uppercase tracking-[0.18em] text-limiar-200">Live</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>

        <section className="mx-auto max-w-6xl px-6 pb-24">
          <div className="overflow-hidden rounded-[36px] border border-white/8 bg-[linear-gradient(135deg,rgba(76,29,149,0.24),rgba(14,165,233,0.12),rgba(5,2,8,0.9))] px-8 py-10 shadow-[0_24px_90px_rgba(76,29,149,0.2)] sm:px-10">
            <div className="grid items-center gap-8 lg:grid-cols-[minmax(0,1.1fr)_auto]">
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-limiar-100">Pronto para entrar</p>
                <h2 className="mt-4 font-display text-4xl font-bold text-white">Comece a campanha com tudo no mesmo lugar.</h2>
                <p className="mt-4 max-w-2xl text-base leading-7 text-slate-200/80">
                  Entre, organize a mesa e mantenha o grupo sincronizado do preparo ate a sessao.
                </p>
              </div>
              <div className="flex flex-col gap-3 sm:flex-row lg:flex-col">
                <Link
                  to={user ? routes.home : routes.register}
                  className="inline-flex items-center justify-center rounded-2xl bg-white px-6 py-3.5 text-sm font-bold text-slate-950 transition-transform hover:scale-[1.02]"
                >
                  {user ? "Ir para o app" : "Criar conta"}
                </Link>
                <Link
                  to={user ? routes.home : routes.login}
                  className="inline-flex items-center justify-center rounded-2xl border border-white/15 bg-white/5 px-6 py-3.5 text-sm font-semibold text-white transition-colors hover:bg-white/10"
                >
                  {user ? "Ver dashboard" : "Entrar"}
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      <footer className="relative z-10 border-t border-white/6 bg-slate-950/60 px-6 py-8 backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl flex-col items-center justify-between gap-4 text-center sm:flex-row sm:text-left">
          <div className="flex items-center gap-4">
            <BrandMark size="md" />
            <div>
              <p className="font-display text-xl font-bold text-white">{APP_NAME}</p>
              <p className="mt-1 text-sm text-slate-500">Campanhas conectadas, fichas vivas e mesas mais bonitas.</p>
            </div>
          </div>
          <div className="text-sm text-slate-500">
            <p>&copy; {currentYear} {APP_NAME}. Todos os direitos reservados.</p>
            <p className="mt-1 text-xs uppercase tracking-[0.24em] text-limiar-200/70">Projeto open source em evolucao</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

const ArrowIcon = ({ className = "" }: { className?: string }) => (
  <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.2}>
    <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 4.5L21 12m0 0l-7.5 7.5M21 12H3" />
  </svg>
);
