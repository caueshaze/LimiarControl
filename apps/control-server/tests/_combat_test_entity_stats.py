import unittest
from unittest.mock import MagicMock, patch

from app.models.base_item import BaseItemWeaponCategory, BaseItemWeaponRangeType
from app.models.campaign_entity import CampaignEntity
from app.models.combat import CombatPhase, CombatState
from app.models.item import Item, ItemType
from app.models.inventory import InventoryItem
from app.models.session_entity import SessionEntity
from app.models.session_state import SessionState
from app.schemas.campaign_entity import CombatAction
from app.schemas.combat import (
    CombatApplyDamageRequest,
    CombatApplyHealingRequest,
    CombatAttackRequest,
    CombatEntityActionRequest,
    CombatParticipant,
    CombatSetInitiativeParticipant,
    CombatSetInitiativeRequest,
    CombatStartRequest,
)
from app.services.combat import (
    CombatService,
    CombatServiceError,
    _parse_dice,
    _roll_dice_expression,
)


class CombatEntityStatsTestsMixin:
    def test_get_stats_handles_null_spellcasting(self):
        session_state = MagicMock()
        session_state.state_json = {
            "abilities": {
                "strength": 16,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 8,
            },
            "equippedArmor": {
                "name": "Leather",
                "baseAC": 11,
                "dexCap": None,
                "armorType": "light",
                "allowsDex": True,
            },
            "equippedShield": {"name": "Shield", "bonus": 2},
            "miscACBonus": 0,
            "level": 1,
            "spellcasting": None,
        }
        result = MagicMock()
        result.first.return_value = session_state
        self.db.exec.return_value = result

        target, ac, str_val, dex_val, prof_bonus, spell_mod = CombatService._get_stats(
            self.db,
            "player-123",
            "player",
            "session-123",
        )

        self.assertIs(target, session_state)
        self.assertEqual(ac, 15)
        self.assertEqual(str_val, 16)
        self.assertEqual(dex_val, 14)
        self.assertEqual(prof_bonus, 2)
        self.assertEqual(spell_mod, 0)

    def test_calculate_player_armor_class_uses_equipped_loadout(self):
        ac = CombatService.calculate_player_armor_class_from_state({
            "class": "fighter",
            "abilities": {
                "strength": 14,
                "dexterity": 14,
                "constitution": 12,
                "intelligence": 10,
                "wisdom": 10,
                "charisma": 8,
            },
            "equippedArmor": {
                "name": "Scale Mail",
                "baseAC": 14,
                "dexCap": 2,
                "armorType": "medium",
                "allowsDex": True,
            },
            "equippedShield": {"name": "Shield", "bonus": 2},
            "miscACBonus": 1,
            "fightingStyle": "defense",
        })

        self.assertEqual(ac, 20)

    def test_build_player_attack_context_uses_current_weapon_proficiency_and_magic_bonus(self):
        session_entry_result = MagicMock()
        session_entry_result.first.return_value = MagicMock(
            id="session-123",
            campaign_id="camp-1",
            party_id="party-1",
        )
        member_result = MagicMock()
        member_result.first.return_value = MagicMock(id="member-1")
        inventory_item_result = MagicMock()
        inventory_item_result.first.return_value = InventoryItem(
            id="inv-1",
            campaign_id="camp-1",
            party_id="party-1",
            member_id="member-1",
            item_id="item-1",
        )
        item_result = MagicMock()
        item_result.first.return_value = Item(
            id="item-1",
            campaign_id="camp-1",
            name="Rapier",
            type=ItemType.WEAPON,
            description="",
            damage_dice="1d8",
            damage_type="piercing",
            properties=["finesse"],
            weapon_category=BaseItemWeaponCategory.MARTIAL,
            weapon_range_type=BaseItemWeaponRangeType.MELEE,
            name_pt_snapshot="Rapieira",
        )
        self.db.exec.side_effect = [
            session_entry_result,
            member_result,
            inventory_item_result,
            item_result,
        ]

        context = CombatService._build_player_attack_context(
            self.db,
            "session-123",
            "player-123",
            {
                "currentWeaponId": "inv-1",
                "level": 5,
                "abilities": {
                    "strength": 12,
                    "dexterity": 16,
                    "constitution": 12,
                    "intelligence": 10,
                    "wisdom": 10,
                    "charisma": 8,
                },
                "weaponProficiencies": ["Marciais"],
                "weapons": [
                    {
                        "name": "Rapieira",
                        "magicBonus": 1,
                        "proficient": True,
                    }
                ],
            },
        )

        self.assertEqual(context["ability"], "dexterity")
        self.assertTrue(context["is_proficient"])
        self.assertEqual(context["attack_bonus"], 7)
        self.assertEqual(context["damage_bonus"], 4)

    def test_entity_save_bonus_prefers_structured_saving_throw_bonus(self):
        session_entity = SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1")
        campaign_entity = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Goblin Adept",
            saving_throws={"dexterity": 5},
            abilities={"dexterity": 8},
        )

        with patch(
            "app.services.combat.CombatService._get_session_entity_and_campaign_entity",
            return_value=(session_entity, campaign_entity),
        ):
            bonus = CombatService._get_save_bonus(
                self.db,
                "session-123",
                "enemy-123",
                "session_entity",
                "dexterity",
            )

        self.assertEqual(bonus, 5)

    def test_entity_save_bonus_falls_back_to_ability_modifier(self):
        session_entity = SessionEntity(id="enemy-123", session_id="session-123", campaign_entity_id="ce-1")
        campaign_entity = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Goblin",
            abilities={"dexterity": 14},
        )

        with patch(
            "app.services.combat.CombatService._get_session_entity_and_campaign_entity",
            return_value=(session_entity, campaign_entity),
        ):
            bonus = CombatService._get_save_bonus(
                self.db,
                "session-123",
                "enemy-123",
                "session_entity",
                "dexterity",
            )

        self.assertEqual(bonus, 2)

    def test_entity_initiative_bonus_uses_override_or_dexterity(self):
        campaign_entity = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Scout",
            initiative_bonus=None,
            abilities={"dexterity": 14},
        )

        self.assertEqual(CombatService._get_entity_initiative_bonus(campaign_entity, {}), 2)
        self.assertEqual(
            CombatService._get_entity_initiative_bonus(campaign_entity, {"initiativeBonus": 5}),
            5,
        )

    def test_entity_skill_bonus_uses_override_or_base_ability(self):
        campaign_entity = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Scout",
            abilities={"dexterity": 14, "wisdom": 12},
            skills={"stealth": 6},
        )

        self.assertEqual(CombatService._get_entity_skill_bonus(campaign_entity, {}, "stealth"), 6)
        self.assertEqual(CombatService._get_entity_skill_bonus(campaign_entity, {}, "perception"), 1)

    @patch("app.services.combat.CombatService._get_campaign_system_for_session", return_value="DND5E")
    @patch("app.services.combat_service.entity_actions.get_base_item_by_canonical_key")
    def test_resolve_weapon_action_prefers_catalog_profile(self, mock_get_base_item, mock_get_system):
        mock_get_base_item.return_value = MagicMock(
            item_kind="weapon",
            damage_dice="1d6",
            damage_type="piercing",
            range_normal_meters=24,
            weapon_range_type="ranged",
        )

        resolved = CombatService._resolve_weapon_combat_action(
            self.db,
            "session-123",
            CombatAction(
                id="shortbow",
                name="Shortbow",
                kind="weapon_attack",
                weaponCanonicalKey="shortbow",
                toHitBonus=4,
                damageBonus=2,
            ),
        )

        self.assertEqual(resolved["damageDice"], "1d6")
        self.assertEqual(resolved["damageType"], "piercing")
        self.assertEqual(resolved["rangeMeters"], 24)
        self.assertEqual(resolved["isMelee"], False)

    def test_resolve_weapon_action_prefers_campaign_item_profile(self):
        session_entry_result = MagicMock()
        session_entry_result.first.return_value = MagicMock(id="session-123", campaign_id="camp-1")
        item_result = MagicMock()
        item_result.first.return_value = Item(
            id="item-1",
            campaign_id="camp-1",
            name="Rusty Spear",
            type=ItemType.WEAPON,
            description="",
            damage_dice="1d6",
            damage_type="piercing",
            range_meters=6,
            weapon_range_type="melee",
            item_kind="weapon",
        )
        self.db.exec.side_effect = [session_entry_result, item_result]

        resolved = CombatService._resolve_weapon_combat_action(
            self.db,
            "session-123",
            CombatAction(
                id="spear",
                name="Spear",
                kind="weapon_attack",
                campaignItemId="item-1",
                toHitBonus=4,
            ),
        )

        self.assertEqual(resolved["campaignItemId"], "item-1")
        self.assertEqual(resolved["damageDice"], "1d6")
        self.assertEqual(resolved["damageType"], "piercing")
        self.assertEqual(resolved["rangeMeters"], 6)
        self.assertEqual(resolved["isMelee"], True)

    @patch("app.services.combat.CombatService._get_spell_catalog_entry_for_session")
    def test_resolve_spell_action_prefers_catalog_spell_data(self, mock_get_spell_catalog):
        mock_get_spell_catalog.return_value = MagicMock(
            saving_throw="dexterity",
            damage_type="fire",
            range_meters=18,
            range_text="120 feet",
        )
        npc = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Shaman",
            spellcasting={"saveDc": 14, "attackBonus": 6},
        )

        resolved = CombatService._resolve_spell_combat_action(
            self.db,
            "session-123",
            npc,
            CombatAction(
                id="flame_burst",
                name="Flame Burst",
                kind="saving_throw",
                spellCanonicalKey="burning_hands",
                damageDice="3d6",
            ),
        )

        self.assertEqual(resolved["saveAbility"], "dexterity")
        self.assertEqual(resolved["saveDc"], 14)
        self.assertEqual(resolved["damageType"], "fire")
        self.assertEqual(resolved["rangeMeters"], 18)
