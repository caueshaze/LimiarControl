from app.services.combat_service.condition_effects_predicates import target_wearing_metal_armor


def test_equipped_metal_armor_returns_true():
    participant = {"equippedArmor": {"armorType": "heavy", "armorMaterial": "metal"}}
    assert target_wearing_metal_armor(participant) is True


def test_equipped_non_metal_armor_returns_false():
    assert target_wearing_metal_armor({"equippedArmor": {"armorType": "light", "armorMaterial": "leather"}}) is False
    assert target_wearing_metal_armor({"equippedArmor": {"armorType": "medium", "armorMaterial": "hide"}}) is False


def test_equipped_armor_unknown_or_missing_returns_false():
    assert target_wearing_metal_armor({"equippedArmor": {"armorType": "heavy", "armorMaterial": None}}) is False
    assert target_wearing_metal_armor({"equippedArmor": {"armorType": "heavy"}}) is False
    assert target_wearing_metal_armor({}) is False


def test_armor_type_none_blocks_metal_material():
    participant = {"equippedArmor": {"armorType": "none", "armorMaterial": "metal"}}
    assert target_wearing_metal_armor(participant) is False


def test_metal_requires_explicit_armor_type_string():
    participant = {"equippedArmor": {"armorMaterial": "metal"}}
    assert target_wearing_metal_armor(participant) is False


def test_shield_metal_alone_does_not_count():
    participant = {"equippedShield": {"armorMaterial": "metal"}}
    assert target_wearing_metal_armor(participant) is False


def test_shield_metal_plus_non_metal_armor_still_false():
    participant = {
        "equippedArmor": {"armorType": "light", "armorMaterial": "leather"},
        "equippedShield": {"armorMaterial": "metal"},
    }
    assert target_wearing_metal_armor(participant) is False


def test_shield_metal_plus_metal_armor_true_due_to_armor():
    participant = {
        "equippedArmor": {"armorType": "heavy", "armorMaterial": "metal"},
        "equippedShield": {"armorMaterial": "metal"},
    }
    assert target_wearing_metal_armor(participant) is True


def test_npc_wearing_metal_armor_policy():
    assert target_wearing_metal_armor({"wearingMetalArmor": True}) is True
    assert target_wearing_metal_armor({"wearingMetalArmor": False}) is False
    assert target_wearing_metal_armor({"wearingMetalArmor": None}) is False
    assert target_wearing_metal_armor({"name": "No Metadata NPC"}) is False


def test_no_heuristics_used():
    assert target_wearing_metal_armor({"armorClass": 18}) is False
    assert target_wearing_metal_armor({"name": "Armored Knight"}) is False
    assert target_wearing_metal_armor({"description": "wears plate armor"}) is False
    assert target_wearing_metal_armor({"equippedArmor": {"armorType": "heavy"}}) is False


def test_malformed_participants_return_false():
    assert target_wearing_metal_armor(None) is False
    assert target_wearing_metal_armor({"equippedArmor": "not-a-dict"}) is False
    assert target_wearing_metal_armor({"equippedShield": "not-a-dict"}) is False


def test_hybrid_explicit_positive_sources():
    assert (
        target_wearing_metal_armor(
            {"equippedArmor": {"armorType": "heavy", "armorMaterial": "metal"}, "wearingMetalArmor": False}
        )
        is True
    )
    assert (
        target_wearing_metal_armor(
            {"equippedArmor": {"armorType": "light", "armorMaterial": "leather"}, "wearingMetalArmor": True}
        )
        is True
    )
