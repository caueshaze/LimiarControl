import { describe, expect, it } from "vitest";
import {
  buildSpiritualWeaponFollowUpAction,
  buildSpiritualWeaponReachableCells,
  buildSpiritualWeaponHighlights,
  buildSpiritualWeaponValidTargets,
} from "./spiritualWeapon";
import type { CombatMapPreviewToken, CombatParticipant, CombatSpellAnchor } from "../../../shared/api/combatRepo";

const makeAnchor = (override: Partial<CombatSpellAnchor> = {}): CombatSpellAnchor => ({
  id: "anchor-1",
  source_spell_key: "spiritual_weapon",
  source_spell_name: "Arma Espiritual",
  owner_participant_id: "p1",
  created_by_participant_id: "p1",
  position: { x: 5, y: 5 },
  duration_type: "rounds",
  remaining_rounds: 8,
  expires_on: "turn_start",
  expires_at_participant_id: "p1",
  render_kind: "spiritual_weapon",
  movement: { max_meters_per_follow_up: 6 },
  metadata: {},
  ...override,
});

const makeParticipant = (override: Partial<CombatParticipant> = {}): CombatParticipant => ({
  id: "participant-1",
  kind: "player",
  ref_id: "ref-1",
  display_name: "Hero",
  initiative: 10,
  status: "active",
  team: "players",
  visible: true,
  actor_user_id: "user-1",
  ...override,
});

const makeToken = (
  combatantId: string,
  x: number,
  y: number,
): CombatMapPreviewToken => ({
  token_id: `token-${combatantId}`,
  label: combatantId,
  position: { x, y },
  combatant_id: combatantId,
  controller_type: "player",
});

describe("buildSpiritualWeaponReachableCells", () => {
  it("returns cells within 6m using Chebyshev distance", () => {
    const cells = buildSpiritualWeaponReachableCells({ x: 0, y: 0 }, 6);
    // Chebyshev 4 cells (6m / 1.5m = 4)
    expect(cells).toContainEqual({ x: 4, y: 4 }); // Chebyshev = 4, included
    expect(cells).not.toContainEqual({ x: 5, y: 0 }); // Chebyshev = 5, excluded
  });

  it("includes the origin cell (stay-in-place via click)", () => {
    const cells = buildSpiritualWeaponReachableCells({ x: 3, y: 3 }, 6);
    expect(cells).toContainEqual({ x: 3, y: 3 });
  });

  it("excludes cells beyond maxCells Chebyshev distance", () => {
    const cells = buildSpiritualWeaponReachableCells({ x: 0, y: 0 }, 6);
    for (const cell of cells) {
      expect(Math.max(Math.abs(cell.x), Math.abs(cell.y))).toBeLessThanOrEqual(4);
    }
  });

  it("offsets results by anchor position", () => {
    const cells = buildSpiritualWeaponReachableCells({ x: 10, y: 10 }, 6);
    expect(cells).toContainEqual({ x: 10, y: 10 }); // origin
    expect(cells).toContainEqual({ x: 14, y: 14 }); // max distance
    expect(cells).not.toContainEqual({ x: 0, y: 0 }); // unrelated cell
  });

  it("handles small range correctly", () => {
    // 1.5m = 1 cell
    const cells = buildSpiritualWeaponReachableCells({ x: 5, y: 5 }, 1.5);
    expect(cells).toContainEqual({ x: 5, y: 5 }); // origin
    expect(cells).toContainEqual({ x: 6, y: 5 });
    expect(cells).not.toContainEqual({ x: 7, y: 5 });
  });
});

describe("buildSpiritualWeaponHighlights", () => {
  it("includes anchor cell as partial status", () => {
    const highlights = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, null, []);
    expect(highlights).toContainEqual({ kind: "area-cell", status: "partial", cell: { x: 5, y: 5 } });
  });

  it("includes selected destination as valid when set", () => {
    const highlights = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, { x: 7, y: 5 }, []);
    expect(highlights).toContainEqual({ kind: "area-cell", status: "valid", cell: { x: 7, y: 5 } });
  });

  it("emits affected-token for each valid target", () => {
    const targets = [
      makeParticipant({ id: "p1", ref_id: "ref-1" }),
      makeParticipant({ id: "p2", ref_id: "ref-2" }),
    ];
    const highlights = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, null, targets);
    expect(highlights).toContainEqual({ kind: "affected-token", status: "valid", targetRefId: "ref-1" });
    expect(highlights).toContainEqual({ kind: "affected-token", status: "valid", targetRefId: "ref-2" });
  });

  it("returns only anchor highlight when no destination and no targets", () => {
    const highlights = buildSpiritualWeaponHighlights({ x: 3, y: 3 }, null, []);
    expect(highlights).toHaveLength(1);
    expect(highlights[0]).toMatchObject({ kind: "area-cell", status: "partial" });
  });
});

describe("buildSpiritualWeaponValidTargets", () => {
  it("filters tokens by Chebyshev <= 1 from final position", () => {
    const participants = [
      makeParticipant({ id: "p1", ref_id: "ref-1" }),
      makeParticipant({ id: "p2", ref_id: "ref-2" }),
    ];
    const mapTokens = [
      makeToken("ref-1", 5, 5), // adjacent (Chebyshev 0)
      makeToken("ref-2", 8, 8), // far away
    ];
    const result = buildSpiritualWeaponValidTargets({
      participants,
      finalAnchorPosition: { x: 5, y: 5 },
      actorParticipantId: null,
      mapTokens,
    });
    expect(result.map((p) => p.id)).toEqual(["p1"]);
  });

  it("excludes dead and defeated participants", () => {
    const participants = [
      makeParticipant({ id: "p1", ref_id: "ref-1", status: "dead" }),
      makeParticipant({ id: "p2", ref_id: "ref-2", status: "defeated" }),
      makeParticipant({ id: "p3", ref_id: "ref-3", status: "active" }),
    ];
    const mapTokens = [
      makeToken("ref-1", 5, 5),
      makeToken("ref-2", 5, 5),
      makeToken("ref-3", 5, 5),
    ];
    const result = buildSpiritualWeaponValidTargets({
      participants,
      finalAnchorPosition: { x: 5, y: 5 },
      actorParticipantId: null,
      mapTokens,
    });
    expect(result.map((p) => p.id)).toEqual(["p3"]);
  });

  it("excludes the caster's own participant", () => {
    const participants = [
      makeParticipant({ id: "caster", ref_id: "caster-ref" }),
      makeParticipant({ id: "enemy", ref_id: "enemy-ref" }),
    ];
    const mapTokens = [
      makeToken("caster-ref", 5, 5),
      makeToken("enemy-ref", 5, 5),
    ];
    const result = buildSpiritualWeaponValidTargets({
      participants,
      finalAnchorPosition: { x: 5, y: 5 },
      actorParticipantId: "caster",
      mapTokens,
    });
    expect(result.map((p) => p.id)).toEqual(["enemy"]);
  });

  it("returns empty when no tokens within reach", () => {
    const participants = [makeParticipant({ id: "p1", ref_id: "ref-1" })];
    const mapTokens = [makeToken("ref-1", 10, 10)];
    const result = buildSpiritualWeaponValidTargets({
      participants,
      finalAnchorPosition: { x: 5, y: 5 },
      actorParticipantId: null,
      mapTokens,
    });
    expect(result).toHaveLength(0);
  });

  it("includes diagonally adjacent tokens (Chebyshev = 1)", () => {
    const participants = [makeParticipant({ id: "p1", ref_id: "ref-1" })];
    const mapTokens = [makeToken("ref-1", 6, 6)]; // diagonal from (5,5)
    const result = buildSpiritualWeaponValidTargets({
      participants,
      finalAnchorPosition: { x: 5, y: 5 },
      actorParticipantId: null,
      mapTokens,
    });
    expect(result).toHaveLength(1);
  });
});

describe("buildSpiritualWeaponFollowUpAction", () => {
  it("returns action when owned spiritual_weapon anchor exists", () => {
    const action = buildSpiritualWeaponFollowUpAction([makeAnchor()], "p1");
    expect(action).not.toBeNull();
    expect(action?.anchorId).toBe("anchor-1");
    expect(action?.position).toEqual({ x: 5, y: 5 });
    expect(action?.remainingRounds).toBe(8);
    expect(action?.maxMovementMeters).toBe(6);
  });

  it("returns null when there are no anchors", () => {
    expect(buildSpiritualWeaponFollowUpAction([], "p1")).toBeNull();
    expect(buildSpiritualWeaponFollowUpAction(null, "p1")).toBeNull();
    expect(buildSpiritualWeaponFollowUpAction(undefined, "p1")).toBeNull();
  });

  it("returns null when participant has no spiritual_weapon anchor", () => {
    const anchor = makeAnchor({ source_spell_key: "hunters_mark" });
    expect(buildSpiritualWeaponFollowUpAction([anchor], "p1")).toBeNull();
  });

  it("returns null when anchor belongs to a different owner", () => {
    const anchor = makeAnchor({ owner_participant_id: "p2" });
    expect(buildSpiritualWeaponFollowUpAction([anchor], "p1")).toBeNull();
  });

  it("returns null when myParticipantId is null or undefined", () => {
    expect(buildSpiritualWeaponFollowUpAction([makeAnchor()], null)).toBeNull();
    expect(buildSpiritualWeaponFollowUpAction([makeAnchor()], undefined)).toBeNull();
  });

  it("uses default 6m movement when movement field is absent", () => {
    const anchor = makeAnchor({ movement: null });
    const action = buildSpiritualWeaponFollowUpAction([anchor], "p1");
    expect(action?.maxMovementMeters).toBe(6);
  });

  it("picks the correct anchor when multiple anchors exist", () => {
    const otherAnchor = makeAnchor({
      id: "anchor-other",
      source_spell_key: "hunters_mark",
    });
    const action = buildSpiritualWeaponFollowUpAction([otherAnchor, makeAnchor()], "p1");
    expect(action?.anchorId).toBe("anchor-1");
  });
});

// ---------------------------------------------------------------------------
// Embedded map / bridge tests (issue #261)
//
// Verify the exact data the shell computes and passes to CombatMapFrame:
//   previewCells  → buildSpiritualWeaponReachableCells(anchor.position, maxMovementMeters)
//   spellHighlights → buildSpiritualWeaponHighlights(anchorPosition, destination, validTargets)
// ---------------------------------------------------------------------------

describe("test_spiritual_weapon_follow_up_passes_anchor_highlights_to_map", () => {
  it("spellHighlights sempre inclui a âncora como area-cell partial", () => {
    const anchorPosition = { x: 5, y: 5 };
    const highlights = buildSpiritualWeaponHighlights(anchorPosition, null, []);
    const anchorHighlight = highlights.find(
      (h) =>
        h.kind === "area-cell" &&
        h.status === "partial" &&
        h.cell.x === anchorPosition.x &&
        h.cell.y === anchorPosition.y,
    );
    expect(anchorHighlight).toBeDefined();
  });

  it("highlight da âncora usa a posição exata do anchor do spell", () => {
    const anchorPosition = { x: 2, y: 9 };
    const highlights = buildSpiritualWeaponHighlights(anchorPosition, null, []);
    expect(highlights).toContainEqual({
      kind: "area-cell",
      status: "partial",
      cell: { x: 2, y: 9 },
    });
  });

  it("affected-token highlights são emitidos para cada alvo válido", () => {
    const targets = [
      makeParticipant({ id: "p1", ref_id: "ref-enemy-1" }),
      makeParticipant({ id: "p2", ref_id: "ref-enemy-2" }),
    ];
    const highlights = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, null, targets);
    expect(highlights).toContainEqual({
      kind: "affected-token",
      status: "valid",
      targetRefId: "ref-enemy-1",
    });
    expect(highlights).toContainEqual({
      kind: "affected-token",
      status: "valid",
      targetRefId: "ref-enemy-2",
    });
  });
});

describe("test_spiritual_weapon_follow_up_passes_reachable_cells_to_map", () => {
  it("previewCells derivam da posição da âncora com distância máxima da magia", () => {
    const anchorPosition = { x: 0, y: 0 };
    const maxMovementMeters = 6; // 4 células Chebyshev
    const cells = buildSpiritualWeaponReachableCells(anchorPosition, maxMovementMeters);
    // Todas as células dentro de 4 Chebyshev devem estar presentes
    expect(cells).toContainEqual({ x: 4, y: 0 });
    expect(cells).toContainEqual({ x: -4, y: 4 });
    expect(cells).toContainEqual({ x: 0, y: 0 }); // origem (sem movimento)
    // Células fora do alcance excluídas
    expect(cells).not.toContainEqual({ x: 5, y: 0 });
  });

  it("previewCells são offset pela posição da âncora, não pela origem do mapa", () => {
    const anchorPosition = { x: 10, y: 8 };
    const cells = buildSpiritualWeaponReachableCells(anchorPosition, 6);
    // Contém âncora + vizinhos próximos
    expect(cells).toContainEqual({ x: 10, y: 8 });
    expect(cells).toContainEqual({ x: 11, y: 8 });
    // Não contém a origem global (0, 0) quando âncora está longe
    expect(cells).not.toContainEqual({ x: 0, y: 0 });
  });

  it("célula da própria âncora está em previewCells (atacar sem mover)", () => {
    const anchorPosition = { x: 7, y: 3 };
    const cells = buildSpiritualWeaponReachableCells(anchorPosition, 6);
    expect(cells).toContainEqual(anchorPosition);
  });
});

describe("test_spiritual_weapon_follow_up_updates_highlights_when_destination_changes", () => {
  it("sem destino: apenas âncora highlight, sem valid area-cell adicional", () => {
    const highlights = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, null, []);
    const areaCells = highlights.filter((h) => h.kind === "area-cell");
    expect(areaCells).toHaveLength(1);
    expect(areaCells[0]).toMatchObject({ status: "partial" });
  });

  it("com destino diferente da âncora: adiciona valid area-cell para o destino", () => {
    const highlights = buildSpiritualWeaponHighlights(
      { x: 5, y: 5 },
      { x: 8, y: 5 },
      [],
    );
    expect(highlights).toContainEqual({
      kind: "area-cell",
      status: "valid",
      cell: { x: 8, y: 5 },
    });
    // Âncora continua presente como partial
    expect(highlights).toContainEqual({
      kind: "area-cell",
      status: "partial",
      cell: { x: 5, y: 5 },
    });
  });

  it("mudança de destino reflete no highlight: coordenadas corretas para cada destino", () => {
    const destA = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, { x: 6, y: 5 }, []);
    const destB = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, { x: 7, y: 7 }, []);

    const validA = destA.find((h) => h.kind === "area-cell" && h.status === "valid");
    const validB = destB.find((h) => h.kind === "area-cell" && h.status === "valid");

    expect(validA?.cell).toEqual({ x: 6, y: 5 });
    expect(validB?.cell).toEqual({ x: 7, y: 7 });
    expect(validA?.cell).not.toEqual(validB?.cell);
  });

  it("limpar o destino remove o valid area-cell dos highlights", () => {
    const withDest = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, { x: 7, y: 5 }, []);
    const withoutDest = buildSpiritualWeaponHighlights({ x: 5, y: 5 }, null, []);

    const validWithDest = withDest.filter((h) => h.kind === "area-cell" && h.status === "valid");
    const validWithoutDest = withoutDest.filter(
      (h) => h.kind === "area-cell" && h.status === "valid",
    );

    expect(validWithDest).toHaveLength(1);
    expect(validWithoutDest).toHaveLength(0);
  });
});
