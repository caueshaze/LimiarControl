import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import {
  getInstanceLabel,
  hasCompleteEffectInstanceTargets,
  InstanceTargetSelector,
  reconcileEffectInstanceTargets,
  type EffectInstanceTargetInput,
} from "./InstanceTargetSelector";

type ReactTestNode = {
  props?: {
    "aria-label"?: string;
    children?: unknown;
    onChange?: (event: { target: { value: string } }) => void;
  };
};

const participants = [
  {
    id: "enemy-1",
    kind: "session_entity" as const,
    ref_id: "session_entity:goblin-a",
    display_name: "Goblin A",
    initiative: 12,
    status: "active" as const,
    team: "enemies" as const,
    visible: true,
    actor_user_id: null,
  },
  {
    id: "enemy-2",
    kind: "session_entity" as const,
    ref_id: "session_entity:goblin-b",
    display_name: "Goblin B",
    initiative: 10,
    status: "active" as const,
    team: "enemies" as const,
    visible: true,
    actor_user_id: null,
  },
];

const findSelectByLabel = (node: unknown, label: string): ReactTestNode | null => {
  if (!node || typeof node !== "object") {
    return null;
  }

  const typedNode = node as ReactTestNode;
  if (typedNode.props?.["aria-label"] === label) {
    return typedNode;
  }

  const children = typedNode.props?.children;
  if (Array.isArray(children)) {
    for (const child of children) {
      const found = findSelectByLabel(child, label);
      if (found) {
        return found;
      }
    }
    return null;
  }

  return findSelectByLabel(children, label);
};

describe("InstanceTargetSelector", () => {
  it("renderiza o numero correto de linhas para instanceCount = 5", () => {
    const markup = renderToStaticMarkup(
      <InstanceTargetSelector
        instanceCount={5}
        participants={participants}
        value={[]}
        onChange={() => undefined}
      />,
    );

    expect(markup.match(/<select/g)?.length).toBe(5);
  });

  it("usa labels Míssil N para magic_missile", () => {
    expect(getInstanceLabel("magic_missile", 3)).toBe("Míssil 3");
  });

  it("usa labels Feixe N para eldritch_blast", () => {
    expect(getInstanceLabel("eldritch_blast", 2)).toBe("Feixe 2");
  });

  it("usa labels Instância N como fallback", () => {
    expect(getInstanceLabel("acid_splash", 4)).toBe("Instância 4");
  });

  it("chama onChange com instance_index e target_ref_id corretos", () => {
    let nextValue: EffectInstanceTargetInput[] = [];
    const tree = InstanceTargetSelector({
      instanceCount: 3,
      participants,
      spellCanonicalKey: "magic_missile",
      value: [],
      onChange: (value) => {
        nextValue = value;
      },
    });

    const select = findSelectByLabel(tree, "Míssil 2");
    expect(select?.props?.onChange).toBeTypeOf("function");

    select?.props?.onChange?.({
      target: { value: "session_entity:goblin-b" },
    });

    expect(nextValue).toEqual([
      {
        instance_index: 2,
        target_ref_id: "session_entity:goblin-b",
      },
    ]);
  });

  it("permite multiplas instancias no mesmo alvo", () => {
    let nextValue: EffectInstanceTargetInput[] = [];
    const firstTree = InstanceTargetSelector({
      instanceCount: 2,
      participants,
      spellCanonicalKey: "magic_missile",
      value: [],
      onChange: (value) => {
        nextValue = value;
      },
    });

    findSelectByLabel(firstTree, "Míssil 1")?.props?.onChange?.({
      target: { value: "session_entity:goblin-a" },
    });

    const secondTree = InstanceTargetSelector({
      instanceCount: 2,
      participants,
      spellCanonicalKey: "magic_missile",
      value: nextValue,
      onChange: (value) => {
        nextValue = value;
      },
    });

    findSelectByLabel(secondTree, "Míssil 2")?.props?.onChange?.({
      target: { value: "session_entity:goblin-a" },
    });

    expect(nextValue).toEqual([
      {
        instance_index: 1,
        target_ref_id: "session_entity:goblin-a",
      },
      {
        instance_index: 2,
        target_ref_id: "session_entity:goblin-a",
      },
    ]);
  });

  it("permite ao pai identificar assignments incompletos", () => {
    expect(
      hasCompleteEffectInstanceTargets(
        [{ instance_index: 1, target_ref_id: "session_entity:goblin-a" }],
        2,
      ),
    ).toBe(false);
    expect(
      hasCompleteEffectInstanceTargets(
        [
          { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
          { instance_index: 2, target_ref_id: "session_entity:goblin-b" },
        ],
        2,
      ),
    ).toBe(true);
  });

  it("reduzir slot remove instancias excedentes e preserva as restantes", () => {
    expect(
      reconcileEffectInstanceTargets(
        [
          { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
          { instance_index: 2, target_ref_id: "session_entity:goblin-a" },
          { instance_index: 3, target_ref_id: "session_entity:goblin-b" },
          { instance_index: 4, target_ref_id: "session_entity:goblin-b" },
          { instance_index: 5, target_ref_id: "session_entity:goblin-c" },
        ],
        3,
      ),
    ).toEqual([
      { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
      { instance_index: 2, target_ref_id: "session_entity:goblin-a" },
      { instance_index: 3, target_ref_id: "session_entity:goblin-b" },
    ]);
  });

  it("aumentar slot adiciona novas instancias usando fallback do alvo atual quando existir", () => {
    expect(
      reconcileEffectInstanceTargets(
        [
          { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
          { instance_index: 2, target_ref_id: "session_entity:goblin-b" },
          { instance_index: 3, target_ref_id: "session_entity:goblin-c" },
        ],
        5,
        "session_entity:goblin-a",
      ),
    ).toEqual([
      { instance_index: 1, target_ref_id: "session_entity:goblin-a" },
      { instance_index: 2, target_ref_id: "session_entity:goblin-b" },
      { instance_index: 3, target_ref_id: "session_entity:goblin-c" },
      { instance_index: 4, target_ref_id: "session_entity:goblin-a" },
      { instance_index: 5, target_ref_id: "session_entity:goblin-a" },
    ]);
  });
});
