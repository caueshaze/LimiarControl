import { useEffect, useState } from "react";

type SessionTimerProps = {
    startedAt: string;
};

export const SessionTimer = ({ startedAt }: SessionTimerProps) => {
    const [elapsed, setElapsed] = useState("00:00:00");

    useEffect(() => {
        const update = () => {
            const start = new Date(startedAt).getTime();
            const now = new Date().getTime();
            const diff = Math.max(0, now - start);

            const hours = Math.floor(diff / (1000 * 60 * 60));
            const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60));
            const seconds = Math.floor((diff % (1000 * 60)) / 1000);

            const fmt = (n: number) => n.toString().padStart(2, "0");
            setElapsed(`${fmt(hours)}:${fmt(minutes)}:${fmt(seconds)}`);
        };

        update();
        const interval = setInterval(update, 1000);
        return () => clearInterval(interval);
    }, [startedAt]);

    return <span className="font-mono tabular-nums">{elapsed}</span>;
};
