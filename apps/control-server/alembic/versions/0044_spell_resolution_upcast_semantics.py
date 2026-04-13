"""spell: reclassify resolution_type and upcast mode semantics

Revision ID: 0044
Revises: 0043_spell_structured_upcast
Create Date: 2026-03-28
"""

from alembic import op
from sqlalchemy import text


revision = "0044"
down_revision = "0043_spell_structured_upcast"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    for table in ("base_spell", "campaign_spell"):
        # --- resolution_type migration ---
        # spell_attack → damage (always has damage)
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'damage' "
            "WHERE resolution_type = 'spell_attack'"
        ))
        # saving_throw WITH damage → damage
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'damage' "
            "WHERE resolution_type = 'saving_throw' "
            "AND (damage_dice IS NOT NULL OR damage_type IS NOT NULL)"
        ))
        # saving_throw WITHOUT damage → control
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'control' "
            "WHERE resolution_type = 'saving_throw' "
            "AND damage_dice IS NULL AND damage_type IS NULL"
        ))
        # automatic WITH damage → damage
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'damage' "
            "WHERE resolution_type = 'automatic' "
            "AND (damage_dice IS NOT NULL OR damage_type IS NOT NULL)"
        ))
        # automatic WITHOUT damage/heal → utility
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'utility' "
            "WHERE resolution_type = 'automatic' "
            "AND damage_dice IS NULL AND damage_type IS NULL AND heal_dice IS NULL"
        ))
        # none → utility
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'utility' "
            "WHERE resolution_type = 'none'"
        ))
        # heal stays heal (no change needed)

        # Clear save_success_outcome where it doesn't belong
        conn.execute(text(
            f"UPDATE {table} SET save_success_outcome = NULL "
            "WHERE resolution_type != 'damage' OR saving_throw IS NULL"
        ))

        # --- upcast_json mode migration ---
        for old_mode, new_mode in [
            ("add_damage", "extra_damage_dice"),
            ("add_heal", "extra_heal_dice"),
            ("increase_targets", "additional_targets"),
            ("custom", "extra_effect"),
        ]:
            conn.execute(text(
                f"UPDATE {table} "
                f"SET upcast_json = jsonb_set(upcast_json, '{{mode}}', '\"{new_mode}\"') "
                f"WHERE upcast_json IS NOT NULL AND upcast_json->>'mode' = '{old_mode}'"
            ))


def downgrade() -> None:
    conn = op.get_bind()
    for table in ("base_spell", "campaign_spell"):
        # Reverse resolution_type (best effort — data loss for buff/debuff/utility/control edge cases)
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'saving_throw' "
            "WHERE resolution_type IN ('control', 'debuff') AND saving_throw IS NOT NULL"
        ))
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'saving_throw' "
            "WHERE resolution_type = 'damage' AND saving_throw IS NOT NULL"
        ))
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'spell_attack' "
            "WHERE resolution_type = 'damage' AND saving_throw IS NULL"
        ))
        conn.execute(text(
            f"UPDATE {table} SET resolution_type = 'automatic' "
            "WHERE resolution_type IN ('utility', 'buff')"
        ))
        for old_mode, new_mode in [
            ("extra_damage_dice", "add_damage"),
            ("extra_heal_dice", "add_heal"),
            ("additional_targets", "increase_targets"),
            ("extra_effect", "custom"),
        ]:
            conn.execute(text(
                f"UPDATE {table} "
                f"SET upcast_json = jsonb_set(upcast_json, '{{mode}}', '\"{new_mode}\"') "
                f"WHERE upcast_json IS NOT NULL AND upcast_json->>'mode' = '{old_mode}'"
            ))
