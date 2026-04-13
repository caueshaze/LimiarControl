import { describe, expect, it } from "vitest";

import {
  getSpellAuthorityReference,
  normalizeSpellAuthorityName,
  resolveSpellByAuthority
} from "./spellAuthority";

describe("spellAuthority", () => {
  it("prefers campaignSpellId over canonicalKey and name", () => {
    expect(
      getSpellAuthorityReference({
        campaignSpellId: "camp-spell-1",
        canonicalKey: "magic_missile",
        name: "Magic Missile"
      })
    ).toEqual({
      kind: "campaign",
      key: "campaign:camp-spell-1",
      value: "camp-spell-1"
    });
  });

  it("falls back to canonicalKey when campaignSpellId is absent", () => {
    expect(
      getSpellAuthorityReference({
        canonicalKey: "magic_missile",
        name: "Magic Missile"
      })
    ).toEqual({
      kind: "canonical",
      key: "canonical:magic_missile",
      value: "magic_missile"
    });
  });

  it("falls back to normalized name when only name exists", () => {
    expect(
      getSpellAuthorityReference({
        name: "  Magic   Missile  "
      })
    ).toEqual({
      kind: "name",
      key: "name:magic missile",
      value: "magic missile"
    });
  });

  it("normalizes fallback names deterministically", () => {
    expect(normalizeSpellAuthorityName("  Hunter's   Mark ")).toBe(
      "hunter's mark"
    );
  });

  it("does not degrade to weaker identifiers when campaignSpellId is present", () => {
    const catalog = [
      {
        campaignSpellId: "camp-spell-2",
        canonicalKey: "magic_missile",
        name: "Magic Missile"
      },
      {
        campaignSpellId: null,
        canonicalKey: "magic_missile",
        name: "Magic Missile"
      }
    ];

    expect(
      resolveSpellByAuthority(catalog, {
        campaignSpellId: "camp-spell-1",
        canonicalKey: "magic_missile",
        name: "Magic Missile"
      })
    ).toBeUndefined();
  });
});
