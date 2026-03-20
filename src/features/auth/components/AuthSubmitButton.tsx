type AuthSubmitButtonProps = {
  loading: boolean;
  idleLabel: string;
  loadingLabel: string;
};

export const AuthSubmitButton = ({
  loading,
  idleLabel,
  loadingLabel,
}: AuthSubmitButtonProps) => (
  <button
    type="submit"
    disabled={loading}
    className="group relative mt-2 w-full overflow-hidden rounded-[24px] border border-limiar-200/20 bg-[linear-gradient(135deg,#c4b5fd_0%,#67e8f9_48%,#fde68a_100%)] px-5 py-4 text-sm font-bold text-slate-950 shadow-[0_18px_50px_rgba(103,232,249,0.18)] transition duration-300 hover:-translate-y-0.5 hover:shadow-[0_24px_70px_rgba(167,139,250,0.28)] active:translate-y-0 disabled:cursor-not-allowed disabled:opacity-70"
  >
    <div className="absolute inset-0 bg-[linear-gradient(120deg,rgba(255,255,255,0.26),transparent_30%,transparent_70%,rgba(255,255,255,0.18))] opacity-0 transition-opacity duration-300 group-hover:opacity-100" />
    <span className="relative z-10 flex items-center justify-center gap-2">
      {loading ? (
        <>
          <span className="h-4 w-4 rounded-full border-2 border-slate-950/20 border-t-slate-950 motion-safe:animate-spin" />
          {loadingLabel}
        </>
      ) : (
        <>
          {idleLabel}
          <span className="transition-transform duration-300 group-hover:translate-x-0.5">
            -&gt;
          </span>
        </>
      )}
    </span>
  </button>
);
