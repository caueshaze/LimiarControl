from __future__ import annotations

from math import floor

from app.services.base_items import get_base_item_by_canonical_key
from app.services.base_spells import get_base_spell_by_canonical_key
from app.schemas.campaign_entity import resolve_saving_throw_bonus as resolve_entity_saving_throw_bonus

from .entity_action_spell import CombatEntitySpellActionMixin
from .entity_action_weapon import CombatEntityWeaponActionMixin
from .exceptions import CombatServiceError


class CombatEntityActionMixin(CombatEntitySpellActionMixin, CombatEntityWeaponActionMixin):
    @classmethod
    def _resolve_entity_combat_action(cls, db, session_id: str, npc, action) -> dict:
        if action.kind == "utility":
            return {"name": action.name, "kind": action.kind, "description": action.description}
        if action.kind == "weapon_attack":
            return cls._resolve_weapon_combat_action(db, session_id, action)
        if action.kind in ("spell_attack", "saving_throw"):
            return cls._resolve_spell_combat_action(db, session_id, npc, action)
        if action.kind == "heal":
            if action.spellCanonicalKey:
                return cls._resolve_spell_combat_action(db, session_id, npc, action)
            return {"name": action.name, "kind": action.kind, "description": action.description, "healDice": action.healDice, "healBonus": action.healBonus or 0}
        raise CombatServiceError("Unsupported combat action kind.")

    @classmethod
    def _get_save_bonus(cls, db, session_id: str, ref_id: str, kind: str, ability_name: str) -> int:
        normalized_ability = cls._normalize_ability_name(ability_name)
        if not normalized_ability:
            raise CombatServiceError("Invalid save ability")
        if kind == "player":
            target_model, *_ = cls._get_stats(db, ref_id, kind, session_id)
            data = cls._as_dict(target_model.state_json)
            abilities = cls._as_dict(data.get("abilities"))
            save_proficiencies = cls._as_dict(data.get("savingThrowProficiencies"))
            level = cls._safe_int(data.get("level"), 1)
            prof_bonus = floor((level - 1) / 4) + 2
            ability_score = cls._safe_int(abilities.get(normalized_ability), 10)
            save_bonus = cls._ability_modifier(ability_score)
            if save_proficiencies.get(normalized_ability) is True:
                save_bonus += prof_bonus
            return save_bonus
        session_entity, npc = cls._get_session_entity_and_campaign_entity(db, ref_id)
        overrides = cls._as_dict(session_entity.overrides)
        abilities = {ability: cls._get_entity_ability_score(cls._as_dict(npc.abilities), overrides, ability) for ability in cls._ENTITY_ABILITY_ALIASES}
        return resolve_entity_saving_throw_bonus(abilities, cls._get_entity_saving_throw_overrides(npc, overrides), normalized_ability)
