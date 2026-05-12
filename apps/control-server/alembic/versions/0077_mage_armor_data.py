"""Insert mage_armor into base_spell and campaign_spell catalogs.

Revision ID: 0077_mage_armor_data
Revises: 0076_combat_game_time_accounting
Create Date: 2026-05-10 00:00:00.000000
"""

import json
from uuid import uuid4

import sqlalchemy as sa
from alembic import op

revision = "0077_mage_armor_data"
down_revision = "0076_combat_game_time_accounting"
branch_labels = None
depends_on = None

_SYSTEM = "DND5E"
_CANONICAL_KEY = "mage_armor"

_EFFECTS_JSON = json.dumps([
    {
        "type": "armor_class_formula",
        "target": "selected_target",
        "duration": {"type": "timed", "seconds": 28800},
        "out_of_combat_duration": {"type": "timed", "seconds": 28800},
        "params": {
            "base_value": 13,
            "ability": "dexterity",
            "requires_unarmored": True,
        },
        "termination_conditions": [{"type": "target_dons_armor"}],
    }
])

_BASE_SPELL_FIELDS = {
    "system": _SYSTEM,
    "canonical_key": _CANONICAL_KEY,
    "name_en": "Mage Armor",
    "name_pt": "Armadura Arcana",
    "description_en": (
        "You touch a willing creature who isn't wearing armor, and a protective magical "
        "force surrounds it until the spell ends. The target's base AC becomes "
        "13 + its Dexterity modifier. The spell ends if the target dons armor or if you "
        "dismiss the spell as an action."
    ),
    "description_pt": (
        "Você toca uma criatura disposta que não está usando armadura, e uma força mágica "
        "protetora a envolve até o final da magia. A CA base do alvo se torna "
        "13 + seu modificador de Destreza. A magia termina se o alvo usar armadura ou se "
        "você dispensar a magia como uma ação."
    ),
    "level": 1,
    "school": "abjuration",
    "classes_json": json.dumps(["Sorcerer", "Wizard"]),
    "casting_time_type": "action",
    "casting_time": "1 action",
    "range_meters": 1,
    "range_text": "Touch",
    "duration": "8 hours",
    "components_json": json.dumps(["V", "S", "M"]),
    "material_component_text": "a piece of cured leather",
    "concentration": False,
    "ritual": False,
    "out_of_combat_castable": True,
    "out_of_combat_target": "self_or_ally",
    "resolution_type": "buff",
    "target_type": "touch",
    "selection_type": "creature",
    "origin_type": "caster",
    "target_anchor": "selected_target",
    "attack_type": "none",
    "range_kind": "touch",
    "effect_timing": "immediate",
    "requires_target_sight": False,
    "requires_target_effect": False,
    "requires_point_sight": False,
    "requires_point_effect": False,
    "effects_json": _EFFECTS_JSON,
    "source": "seed_json_bootstrap",
    "is_srd": True,
    "is_active": True,
}


def upgrade() -> None:
    conn = op.get_bind()

    # ── 1. Upsert base_spell ──────────────────────────────────────────────────
    existing = conn.execute(
        sa.text(
            "SELECT id FROM base_spell WHERE system = :sys AND canonical_key = :key"
        ),
        {"sys": _SYSTEM, "key": _CANONICAL_KEY},
    ).first()

    if existing:
        base_spell_id = existing[0]
        conn.execute(
            sa.text(
                """
                UPDATE base_spell SET
                    name_en = :name_en,
                    name_pt = :name_pt,
                    description_en = :description_en,
                    description_pt = :description_pt,
                    level = :level,
                    school = :school,
                    classes_json = CAST(:classes_json AS jsonb),
                    casting_time_type = :casting_time_type,
                    casting_time = :casting_time,
                    range_meters = :range_meters,
                    range_text = :range_text,
                    duration = :duration,
                    components_json = CAST(:components_json AS jsonb),
                    material_component_text = :material_component_text,
                    concentration = :concentration,
                    ritual = :ritual,
                    out_of_combat_castable = :out_of_combat_castable,
                    out_of_combat_target = :out_of_combat_target,
                    resolution_type = :resolution_type,
                    target_type = :target_type,
                    selection_type = :selection_type,
                    origin_type = :origin_type,
                    target_anchor = :target_anchor,
                    attack_type = :attack_type,
                    range_kind = :range_kind,
                    effect_timing = :effect_timing,
                    requires_target_sight = :requires_target_sight,
                    requires_target_effect = :requires_target_effect,
                    requires_point_sight = :requires_point_sight,
                    requires_point_effect = :requires_point_effect,
                    effects_json = CAST(:effects_json AS jsonb),
                    source = :source,
                    is_srd = :is_srd,
                    is_active = :is_active
                WHERE id = :id
                """
            ),
            {**_BASE_SPELL_FIELDS, "id": base_spell_id},
        )
    else:
        base_spell_id = str(uuid4())
        conn.execute(
            sa.text(
                """
                INSERT INTO base_spell (
                    id, system, canonical_key,
                    name_en, name_pt, description_en, description_pt,
                    level, school, classes_json,
                    casting_time_type, casting_time,
                    range_meters, range_text, duration,
                    components_json, material_component_text,
                    concentration, ritual,
                    out_of_combat_castable, out_of_combat_target,
                    resolution_type,
                    target_type, selection_type, origin_type, target_anchor,
                    attack_type, range_kind, effect_timing,
                    requires_target_sight, requires_target_effect,
                    requires_point_sight, requires_point_effect,
                    effects_json, source, is_srd, is_active
                ) VALUES (
                    :id, :system, :canonical_key,
                    :name_en, :name_pt, :description_en, :description_pt,
                    :level, :school, CAST(:classes_json AS jsonb),
                    :casting_time_type, :casting_time,
                    :range_meters, :range_text, :duration,
                    CAST(:components_json AS jsonb), :material_component_text,
                    :concentration, :ritual,
                    :out_of_combat_castable, :out_of_combat_target,
                    :resolution_type,
                    :target_type, :selection_type, :origin_type, :target_anchor,
                    :attack_type, :range_kind, :effect_timing,
                    :requires_target_sight, :requires_target_effect,
                    :requires_point_sight, :requires_point_effect,
                    CAST(:effects_json AS jsonb), :source, :is_srd, :is_active
                )
                """
            ),
            {**_BASE_SPELL_FIELDS, "id": base_spell_id},
        )

    # ── 2. Backfill campaign_spell for campaigns that lack the canonical key ──
    campaigns = conn.execute(
        sa.text("SELECT id FROM campaign WHERE system = :sys"),
        {"sys": _SYSTEM},
    ).fetchall()

    for (campaign_id,) in campaigns:
        already = conn.execute(
            sa.text(
                "SELECT 1 FROM campaign_spell "
                "WHERE campaign_id = :cid AND canonical_key = :key"
            ),
            {"cid": campaign_id, "key": _CANONICAL_KEY},
        ).first()
        if already:
            continue

        conn.execute(
            sa.text(
                """
                INSERT INTO campaign_spell (
                    id, campaign_id, base_spell_id, canonical_key,
                    name_en, name_pt, description_en, description_pt,
                    level, school, classes_json,
                    casting_time_type, casting_time,
                    range_meters, range_text, duration,
                    components_json, material_component_text,
                    concentration, ritual,
                    out_of_combat_castable, out_of_combat_target,
                    resolution_type,
                    target_type, selection_type, origin_type, target_anchor,
                    attack_type, range_kind, effect_timing,
                    requires_target_sight, requires_target_effect,
                    requires_point_sight, requires_point_effect,
                    effects_json, source, is_srd, is_enabled, is_custom
                ) VALUES (
                    :id, :campaign_id, :base_spell_id, :canonical_key,
                    :name_en, :name_pt, :description_en, :description_pt,
                    :level, :school, CAST(:classes_json AS jsonb),
                    :casting_time_type, :casting_time,
                    :range_meters, :range_text, :duration,
                    CAST(:components_json AS jsonb), :material_component_text,
                    :concentration, :ritual,
                    :out_of_combat_castable, :out_of_combat_target,
                    :resolution_type,
                    :target_type, :selection_type, :origin_type, :target_anchor,
                    :attack_type, :range_kind, :effect_timing,
                    :requires_target_sight, :requires_target_effect,
                    :requires_point_sight, :requires_point_effect,
                    CAST(:effects_json AS jsonb), :source, :is_srd, :is_enabled, :is_custom
                )
                """
            ),
            {
                **_BASE_SPELL_FIELDS,
                "id": str(uuid4()),
                "campaign_id": campaign_id,
                "base_spell_id": base_spell_id,
                "is_enabled": True,
                "is_custom": False,
            },
        )


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(
        sa.text(
            "DELETE FROM campaign_spell "
            "WHERE canonical_key = :key AND source = 'seed_json_bootstrap'"
        ),
        {"key": _CANONICAL_KEY},
    )
    conn.execute(
        sa.text(
            "DELETE FROM base_spell WHERE system = :sys AND canonical_key = :key"
        ),
        {"sys": _SYSTEM, "key": _CANONICAL_KEY},
    )
