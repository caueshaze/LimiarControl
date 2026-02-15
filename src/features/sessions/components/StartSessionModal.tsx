import { useState } from "react";
import { useLocale } from "../../../shared/hooks/useLocale";

type StartSessionModalProps = {
    isOpen: boolean;
    onClose: () => void;
    onConfirm: (name: string, date: string) => void;
    loading?: boolean;
};

export const StartSessionModal = ({
    isOpen,
    onClose,
    onConfirm,
    loading,
}: StartSessionModalProps) => {
    const { t } = useLocale();
    const [name, setName] = useState("");
    // Default to current datetime-local
    const [date, setDate] = useState(() => {
        const now = new Date();
        // Offset for local timezone
        now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
        return now.toISOString().slice(0, 16);
    });

    if (!isOpen) return null;

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        onConfirm(name, date);
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 px-4 backdrop-blur-sm">
            <div className="w-full max-w-md rounded-3xl border border-slate-800 bg-void-950 p-6 shadow-2xl">
                <h2 className="text-xl font-semibold text-white">
                    {"Start Session"}
                </h2>
                <p className="mt-2 text-sm text-slate-400">
                    {"Enter details to begin a new session."}
                </p>

                <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                    <div>
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {"Session Name"}
                        </label>
                        <input
                            autoFocus
                            value={name}
                            onChange={(e) => setName(e.target.value)}
                            placeholder="e.g. The Dark Forest"
                            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none"
                            required
                        />
                    </div>

                    <div>
                        <label className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                            {"Session Date"}
                        </label>
                        <input
                            type="datetime-local"
                            value={date}
                            onChange={(e) => setDate(e.target.value)}
                            className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:border-limiar-500 focus:outline-none placeholder-slate-600 [&::-webkit-calendar-picker-indicator]:invert"
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
                            {"Cancel"}
                        </button>
                        <button
                            type="submit"
                            disabled={loading || !name.trim()}
                            className="flex-1 rounded-full bg-limiar-500 px-4 py-2 text-sm font-semibold text-white hover:bg-limiar-400 disabled:opacity-50"
                        >
                            {loading ? "Starting..." : "Start Session"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
};
