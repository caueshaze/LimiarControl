import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { routes } from "../../app/routes/routes";
import { authRepo } from "../../shared/api/authRepo";
import { useAuth } from "../../features/auth";
import { StepWelcome } from "./steps/StepWelcome";
import { StepProfile } from "./steps/StepProfile";
import { StepToken } from "./steps/StepToken";
import { StepExperience } from "./steps/StepExperience";

type Step = 0 | 1 | 2 | 3;
type ExperienceMode = "GM" | "PLAYER";

const EXPERIENCE_MODE_KEY = "limiar_experience_mode";

export const WelcomePage = () => {
  const navigate = useNavigate();
  const { user, refreshUser } = useAuth();
  const [step, setStep] = useState<Step>(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const [nickname, setNickname] = useState(user?.displayName ?? "");
  const [avatarUrl, setAvatarUrl] = useState<string | null>(null);
  const [tokenColor, setTokenColor] = useState<string | null>(null);
  const [tokenImageUrl, setTokenImageUrl] = useState<string | null>(null);
  const [experienceMode, setExperienceMode] = useState<ExperienceMode | null>(null);

  const handleFinish = async () => {
    setSubmitting(true);
    setSubmitError(null);
    try {
      await authRepo.updateProfile({
        displayName: nickname.trim() || undefined,
        avatarUrl,
        tokenColor,
        tokenImageUrl,
        markOnboarded: true,
      });
      if (experienceMode) {
        localStorage.setItem(EXPERIENCE_MODE_KEY, experienceMode);
      }
      await refreshUser();
      navigate(routes.home);
    } catch (err) {
      const message = err instanceof Error ? err.message : "Falha ao salvar perfil.";
      setSubmitError(message);
    } finally {
      setSubmitting(false);
    }
  };

  const TOTAL_STEPS = 4;

  return (
    <main className="relative min-h-screen overflow-hidden bg-void-950">
      {/* Atmospheric orbs */}
      <div
        aria-hidden
        className="pointer-events-none absolute -left-32 top-10 h-[420px] w-[420px] rounded-full bg-limiar-500/20 blur-[140px] motion-safe:animate-[landing-drift_18s_ease-in-out_infinite]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute right-0 top-0 h-[360px] w-[360px] rounded-full bg-sky-400/14 blur-[140px] motion-safe:animate-[landing-drift_22s_ease-in-out_infinite_reverse]"
      />
      <div
        aria-hidden
        className="pointer-events-none absolute -bottom-24 left-1/3 h-[340px] w-[340px] rounded-full bg-amber-400/10 blur-[160px] motion-safe:animate-[landing-float_16s_ease-in-out_infinite]"
      />

      <div className="relative flex min-h-screen items-center justify-center px-6 py-10">
        <div className="w-full max-w-2xl">
          {/* Step indicator dots */}
          <div className="mb-6 flex items-center justify-center gap-2">
            {Array.from({ length: TOTAL_STEPS }).map((_, idx) => (
              <span
                key={idx}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  idx === step
                    ? "w-8 bg-limiar-400"
                    : idx < step
                      ? "w-4 bg-limiar-500/70"
                      : "w-4 bg-white/10"
                }`}
              />
            ))}
          </div>

          {/* Card */}
          <div
            key={step}
            className="animate-[landing-rise_0.55s_ease-out] rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(17,24,39,0.85),rgba(2,6,23,0.94))] p-8 shadow-[0_30px_80px_rgba(0,0,0,0.45)] backdrop-blur-xl"
          >
            {step === 0 && (
              <StepWelcome onNext={() => setStep(1)} />
            )}
            {step === 1 && (
              <StepProfile
                nickname={nickname}
                avatarUrl={avatarUrl}
                onNicknameChange={setNickname}
                onAvatarChange={setAvatarUrl}
                onBack={() => setStep(0)}
                onNext={() => setStep(2)}
              />
            )}
            {step === 2 && (
              <StepToken
                tokenColor={tokenColor}
                tokenImageUrl={tokenImageUrl}
                onColorChange={setTokenColor}
                onImageChange={setTokenImageUrl}
                onBack={() => setStep(1)}
                onNext={() => setStep(3)}
              />
            )}
            {step === 3 && (
              <StepExperience
                mode={experienceMode}
                onModeChange={setExperienceMode}
                onBack={() => setStep(2)}
                onFinish={handleFinish}
                submitting={submitting}
                submitError={submitError}
              />
            )}
          </div>
        </div>
      </div>
    </main>
  );
};
