import { useState } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";

type StartSessionModalProps = {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (title: string, initialGameTimeSeconds: number) => void;
    loading?: boolean;
};

export const StartSessionModal = ({
    isOpen,
    onClose,
    onConfirm,
    loading,
}: StartSessionModalProps) => {
    const { t } = useLocale();
    const [title, setTitle] = useState("");
    const [startTime, setStartTime] = useState("");

    if (!isOpen) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!startTime) return;
        const [hoursRaw, minutesRaw] = startTime.split(":");
        const hours = Number(hoursRaw);
        const minutes = Number(minutesRaw);
        if (
            Number.isNaN(hours) ||
            Number.isNaN(minutes) ||
            hours < 0 ||
            hours > 23 ||
            minutes < 0 ||
            minutes > 59
        ) {
            return;
        }
        const initialGameTimeSeconds = (hours * 60 + minutes) * 60;
        onConfirm(title, initialGameTimeSeconds);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-void-950 p-6 shadow-2xl">
                <h2 className="text-xl font-semibold text-white">{t("campaignHome.startSession")}</h2>
                <p className="mt-2 text-sm text-slate-400">
                    {t("campaignHome.startSessionHelper")}
                </p>

                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                    <div>
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {t("campaignHome.sessionTitle")}
                        </label>
                        <input
                            autoFocus
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            placeholder={t("campaignHome.sessionNamePlaceholder")}
                            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
                            required
                        />
                    </div>

                    <div>
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {t("campaignHome.sessionStartTime")}
                        </label>
                        <input
                            type="time"
                            value={startTime}
                            onChange={(e) => setStartTime(e.target.value)}
                            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
                            required
                        />
                    </div>

                    <div className="mt-6 flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            disabled={loading}
                            className="flex-1 rounded-full border border-slate-700 px-4 py-2 text-sm font-semibold text-slate-300 hover:border-slate-500 disabled:opacity-50"
                        >
                            {t("common.close")}
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !title.trim() || !startTime}
                            className="flex-1 rounded-full bg-limiar-500 px-4 py-2 text-sm font-semibold text-white hover:bg-limiar-400 disabled:opacity-50"
                        >
                            {loading ? t("campaignHome.starting") : t("campaignHome.startSession")}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
