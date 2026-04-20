import React, { useSyncExternalStore } from "react";
import type { Token } from "@limiarmap/shared-contracts";
import { useEncounterSnapshot } from "../../services/session-store";
import { useCurrentActor } from "../../services/centrifugo-client";
import { battleMapStore } from "./battle-map-store";

const KIND_COLOR: Record<string, string> = {
  playerCharacter: "#2a7abf",
  ally: "#2d7a3a",
  enemy: "#bf3030",
  neutral: "#8a6d3b",
};

function TokenChip({
  token,
  isPlacing,
  onClick,
}: {
  token: Token;
  isPlacing: boolean;
  onClick: () => void;
}): React.JSX.Element {
  const color = KIND_COLOR[token.kind] ?? "#607090";
  const hasDefaultPos = token.position.x === 0 && token.position.y === 0;

  return (
    <button
      onClick={onClick}
      style={{
        display: "flex",
        alignItems: "center",
        gap: 6,
        padding: "5px 10px",
        borderRadius: 5,
        border: `1px solid ${isPlacing ? color : "rgba(255,255,255,0.1)"}`,
        background: isPlacing ? `${color}22` : "rgba(255,255,255,0.04)",
        cursor: "pointer",
        outline: "none",
        flexShrink: 0,
        transition: "border-color 0.15s, background 0.15s",
        boxShadow: isPlacing ? `0 0 0 2px ${color}55` : "none",
      }}
    >
      <span
        style={{
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: color,
          flexShrink: 0,
          boxShadow: isPlacing ? `0 0 4px ${color}` : "none",
        }}
      />
      <span style={{ fontSize: 12, color: isPlacing ? "#fff" : "#b0bcd0", fontWeight: isPlacing ? 600 : 400 }}>
        {token.label}
      </span>
      <span
        style={{
          fontSize: 10,
          color: hasDefaultPos ? "#4a5a6a" : "#5a8a6a",
          marginLeft: 2,
          fontFamily: "monospace",
        }}
      >
        {hasDefaultPos ? "—" : `${token.position.x},${token.position.y}`}
      </span>
    </button>
  );
}

export function TokenPlacementBar(): React.JSX.Element | null {
  const encounter = useEncounterSnapshot();
  const currentActor = useCurrentActor();
  const placingTokenId = useSyncExternalStore(
    (cb) => battleMapStore.subscribe(cb),
    () => battleMapStore.getState().placingTokenId,
    () => battleMapStore.getState().placingTokenId,
  );

  if (!encounter || currentActor.actorType !== "gm") {
    return null;
  }

  const { tokens } = encounter;

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        padding: "7px 10px",
        background: "#0d1520",
        border: "1px solid #1e3050",
        borderRadius: 6,
        flexWrap: "wrap",
        flexShrink: 0,
      }}
    >
      <span
        style={{
          fontSize: 10,
          textTransform: "uppercase",
          letterSpacing: "0.1em",
          color: "#3d6080",
          flexShrink: 0,
          marginRight: 4,
        }}
      >
        {placingTokenId ? "Clique no mapa para posicionar" : "Posicionamento inicial"}
      </span>
      {tokens.map((token) => (
        <TokenChip
          key={token.id}
          token={token}
          isPlacing={placingTokenId === token.id}
          onClick={() =>
            battleMapStore.setPlacingTokenId(
              placingTokenId === token.id ? null : token.id
            )
          }
        />
      ))}
    </div>
  );
}
