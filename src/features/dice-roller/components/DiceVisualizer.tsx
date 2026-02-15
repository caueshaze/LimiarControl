import { useEffect, useState } from "react";
import { type RollEvent } from "../../../entities/roll";
import { useLocale } from "../../../shared/hooks/useLocale";

type DiceVisualizerProps = {
    events: RollEvent[];
};

export const DiceVisualizer = ({ events }: DiceVisualizerProps) => {
    const { t } = useLocale();
    const [activeRoll, setActiveRoll] = useState<RollEvent | null>(null);
    const [show, setShow] = useState(false);

    useEffect(() => {
        if (events.length === 0) return;

        // Check if the latest event is new (less than 5 seconds old)
        const latest = events[0];
        const now = new Date().getTime();
        const eventTime = new Date(latest.createdAt).getTime();

        // Only show if it's recent (within 5s) to avoid showing old rolls on reload
        if (now - eventTime < 5000) {
            setActiveRoll(latest);
            setShow(true);

            const timer = setTimeout(() => {
                setShow(false);
                setActiveRoll(null);
            }, 4000);
            return () => clearTimeout(timer);
        }
    }, [events]);

    if (!show || !activeRoll) return null;

    return (
        <div className="fixed inset-0 z-[100] flex items-center justify-center pointer-events-none">
            <div className="animate-bounce-in flex flex-col items-center">
                {/* Dice GFX Container */}
                <div className="relative">
                    <div className="absolute inset-0 animate-pulse bg-limiar-500/20 blur-3xl rounded-full" />
                    <div className="relative flex h-32 w-32 items-center justify-center rounded-2xl border-4 border-limiar-400 bg-void-950 text-6xl font-black text-white shadow-2xl shadow-limiar-500/50">
                        {activeRoll.total}
                    </div>
                </div>

                {/* Roll Info */}
                <div className="mt-6 rounded-xl bg-slate-900/90 px-6 py-3 text-center shadow-xl backdrop-blur-md border border-slate-800">
                    <p className="text-lg font-bold text-white uppercase tracking-wider">
                        {activeRoll.authorName}
                    </p>
                    <p className="text-sm text-limiar-300 font-mono mt-1">
                        {activeRoll.expression} {activeRoll.label ? `· ${activeRoll.label}` : ""}
                    </p>
                    {activeRoll.results.length > 1 && (
                        <p className="mt-2 text-xs text-slate-400">
                            [{activeRoll.results.join(", ")}]
                        </p>
                    )}
                </div>
            </div>
        </div>
    );
};
