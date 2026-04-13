from datetime import datetime, timezone
import unittest

from pydantic import ValidationError

from app.api.routes.campaign_entities import to_campaign_entity_read
from app.models.campaign_entity import CampaignEntity
from app.schemas.campaign_entity import (
    CampaignEntityCreate,
    ability_modifier,
    resolve_initiative_bonus,
    resolve_saving_throw_bonus,
    resolve_skill_bonus,
)


class TestCampaignEntityStatblock(unittest.TestCase):
    def test_campaign_entity_create_accepts_structured_statblock(self):
        payload = CampaignEntityCreate(
            name="Goblin Shaman",
            category="enemy",
            size="small",
            creatureType="humanoid",
            creatureSubtype="goblinoid",
            armorClass=13,
            maxHp=22,
            speedMeters=9,
            initiativeBonus=2,
            abilities={
                "strength": 8,
                "dexterity": 14,
                "constitution": 10,
                "intelligence": 12,
                "wisdom": 13,
                "charisma": 9,
            },
            savingThrows={"wisdom": 3},
            skills={"stealth": 6, "perception": 3},
            senses={"darkvisionMeters": 18, "passivePerception": 13},
            spellcasting={"ability": "wisdom", "saveDc": 12, "attackBonus": 4},
            damageResistances=["fire"],
            conditionImmunities=["poisoned"],
            combatActions=[
                {
                    "id": "shadow_bolt",
                    "name": "Shadow Bolt",
                    "kind": "spell_attack",
                    "spellCanonicalKey": "witch_bolt",
                    "damageDice": "1d8",
                    "damageType": "force",
                }
            ],
        )

        self.assertEqual(payload.armorClass, 13)
        self.assertEqual(payload.abilities.dexterity, 14)
        self.assertEqual(payload.savingThrows["wisdom"], 3)
        self.assertEqual(payload.skills["stealth"], 6)
        self.assertEqual(payload.senses.darkvisionMeters, 18)
        self.assertEqual(payload.spellcasting.saveDc, 12)

    def test_campaign_entity_create_prunes_redundant_derived_overrides(self):
        payload = CampaignEntityCreate(
            name="Scout",
            abilities={
                "strength": 10,
                "dexterity": 14,
                "constitution": 10,
                "intelligence": 10,
                "wisdom": 12,
                "charisma": 8,
            },
            initiativeBonus=2,
            savingThrows={"dexterity": 2, "wisdom": 3},
            skills={"acrobatics": 2, "stealth": 6},
        )

        self.assertIsNone(payload.initiativeBonus)
        self.assertEqual(payload.savingThrows, {"wisdom": 3})
        self.assertEqual(payload.skills, {"stealth": 6})

    def test_campaign_entity_create_rejects_invalid_damage_type(self):
        with self.assertRaises(ValidationError):
            CampaignEntityCreate(
                name="Broken Ooze",
                combatActions=[
                    {
                        "id": "acid_splash",
                        "name": "Acid Splash",
                        "kind": "spell_attack",
                        "spellCanonicalKey": "acid_splash",
                        "damageDice": "1d6",
                        "damageType": "lava",
                    }
                ],
            )

    def test_to_campaign_entity_read_serializes_structured_statblock(self):
        entity = CampaignEntity(
            id="ce-1",
            campaign_id="camp-1",
            name="Ghoul",
            category="creature",
            size="medium",
            creature_type="undead",
            armor_class=12,
            max_hp=22,
            speed_meters=9,
            initiative_bonus=2,
            abilities={
                "strength": 13,
                "dexterity": 15,
                "constitution": 10,
                "intelligence": 7,
                "wisdom": 10,
                "charisma": 6,
            },
            saving_throws={"dexterity": 4},
            skills={"perception": 2},
            senses={"darkvisionMeters": 18, "passivePerception": 12},
            spellcasting={"ability": "wisdom", "saveDc": 11},
            damage_resistances=["cold"],
            damage_immunities=["poison"],
            damage_vulnerabilities=["radiant"],
            condition_immunities=["poisoned"],
            combat_actions=[
                {
                    "id": "claws",
                    "name": "Claws",
                    "kind": "weapon_attack",
                    "toHitBonus": 4,
                    "damageDice": "2d4",
                    "damageType": "slashing",
                    "isMelee": True,
                }
            ],
            created_at=datetime.now(timezone.utc),
        )

        serialized = to_campaign_entity_read(entity)

        self.assertEqual(serialized.creatureType, "undead")
        self.assertEqual(serialized.maxHp, 22)
        self.assertEqual(serialized.abilities.dexterity, 15)
        self.assertEqual(serialized.savingThrows["dexterity"], 4)
        self.assertEqual(serialized.skills["perception"], 2)
        self.assertEqual(serialized.senses.darkvisionMeters, 18)
        self.assertEqual(serialized.spellcasting.saveDc, 11)
        self.assertEqual(serialized.damageImmunities, ["poison"])
        self.assertEqual(serialized.combatActions[0].name, "Claws")

    def test_serialization_normalizes_redundant_overrides(self):
        entity = CampaignEntity(
            id="ce-2",
            campaign_id="camp-1",
            name="Bandit",
            category="enemy",
            initiative_bonus=2,
            abilities={
                "strength": 10,
                "dexterity": 14,
                "constitution": 10,
                "intelligence": 10,
                "wisdom": 12,
                "charisma": 8,
            },
            saving_throws={"dexterity": 2, "wisdom": 3},
            skills={"acrobatics": 2, "stealth": 6},
            created_at=datetime.now(timezone.utc),
        )

        serialized = to_campaign_entity_read(entity)

        self.assertIsNone(serialized.initiativeBonus)
        self.assertEqual(serialized.savingThrows, {"wisdom": 3})
        self.assertEqual(serialized.skills, {"stealth": 6})

    def test_resolvers_follow_attribute_fallback_and_explicit_overrides(self):
        abilities = {
            "strength": 10,
            "dexterity": 14,
            "constitution": 10,
            "intelligence": 8,
            "wisdom": 12,
            "charisma": 16,
        }

        self.assertEqual(ability_modifier(14), 2)
        self.assertEqual(resolve_initiative_bonus(abilities, None), 2)
        self.assertEqual(resolve_initiative_bonus(abilities, 5), 5)
        self.assertEqual(resolve_saving_throw_bonus(abilities, {}, "wisdom"), 1)
        self.assertEqual(resolve_saving_throw_bonus(abilities, {"wisdom": 4}, "wisdom"), 4)
        self.assertEqual(resolve_skill_bonus(abilities, {}, "deception"), 3)
        self.assertEqual(resolve_skill_bonus(abilities, {"deception": 6}, "deception"), 6)

    def test_combat_action_requires_catalog_for_automated_spell_actions(self):
        with self.assertRaises(ValidationError):
            CampaignEntityCreate(
                name="Broken Mage",
                combatActions=[
                    {
                        "id": "bolt",
                        "name": "Bolt",
                        "kind": "spell_attack",
                        "damageDice": "1d8",
                        "damageType": "force",
                    }
                ],
            )

    def test_utility_action_rejects_executable_fields(self):
        with self.assertRaises(ValidationError):
            CampaignEntityCreate(
                name="Broken Manual Action",
                combatActions=[
                    {
                        "id": "fake",
                        "name": "Fake Spell",
                        "kind": "utility",
                        "damageDice": "1d8",
                    }
                ],
            )

    def test_weapon_action_accepts_campaign_item_reference(self):
        payload = CampaignEntityCreate(
            name="Bandit",
            combatActions=[
                {
                    "id": "scimitar",
                    "name": "Scimitar",
                    "kind": "weapon_attack",
                    "campaignItemId": "item-123",
                    "toHitBonus": 4,
                }
            ],
        )

        self.assertEqual(payload.combatActions[0].campaignItemId, "item-123")


if __name__ == "__main__":
    unittest.main()
