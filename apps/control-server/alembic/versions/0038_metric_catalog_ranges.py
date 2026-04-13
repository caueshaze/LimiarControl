"""Normalize catalog distances to meters and remove CSV item source legacy.

Revision ID: 0038_metric_catalog_ranges
Revises: 0037_item_property_slugs
Create Date: 2026-03-24
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0038_metric_catalog_ranges"
down_revision: Union[str, None] = "0037_item_property_slugs"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_spell_range_meters(table_name: str) -> None:
    op.execute(
        sa.text(
            f"""
            UPDATE {table_name}
            SET range_meters = GREATEST(
                1,
                ROUND(
                    (
                        regexp_match(
                            lower(range_text),
                            '^\\s*([0-9]+)\\s*(feet|foot|ft)\\b'
                        )
                    )[1]::numeric * 0.3048
                )
            )
            WHERE range_text ~* '^\\s*[0-9]+\\s*(feet|foot|ft)\\b'
              AND range_meters IS NULL
            """
        )
    )


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET range_normal = GREATEST(1, ROUND(range_normal * 0.3048))
            WHERE range_normal IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET range_long = GREATEST(1, ROUND(range_long * 0.3048))
            WHERE range_long IS NOT NULL
            """
        )
    )
    op.alter_column("base_item", "range_normal", new_column_name="range_normal_meters")
    op.alter_column("base_item", "range_long", new_column_name="range_long_meters")

    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET source = 'seed_json_bootstrap'
            WHERE source = 'csv_import'
            """
        )
    )
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source TYPE TEXT USING source::TEXT"))
    op.execute(sa.text("ALTER TYPE baseitemsource RENAME TO baseitemsource_old"))
    op.execute(sa.text("CREATE TYPE baseitemsource AS ENUM ('admin_panel', 'seed_json_bootstrap')"))
    op.execute(
        sa.text(
            """
            ALTER TABLE base_item
            ALTER COLUMN source TYPE baseitemsource
            USING source::baseitemsource
            """
        )
    )
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source SET DEFAULT 'admin_panel'"))
    op.execute(sa.text("DROP TYPE baseitemsource_old"))

    op.add_column("base_spell", sa.Column("range_meters", sa.Integer(), nullable=True))
    op.add_column("campaign_spell", sa.Column("range_meters", sa.Integer(), nullable=True))
    _backfill_spell_range_meters("base_spell")
    _backfill_spell_range_meters("campaign_spell")


def downgrade() -> None:
    op.drop_column("campaign_spell", "range_meters")
    op.drop_column("base_spell", "range_meters")

    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source DROP DEFAULT"))
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source TYPE TEXT USING source::TEXT"))
    op.execute(sa.text("ALTER TYPE baseitemsource RENAME TO baseitemsource_new"))
    op.execute(
        sa.text(
            "CREATE TYPE baseitemsource AS ENUM ('admin_panel', 'csv_import', 'seed_json_bootstrap')"
        )
    )
    op.execute(
        sa.text(
            """
            ALTER TABLE base_item
            ALTER COLUMN source TYPE baseitemsource
            USING source::baseitemsource
            """
        )
    )
    op.execute(sa.text("ALTER TABLE base_item ALTER COLUMN source SET DEFAULT 'admin_panel'"))
    op.execute(sa.text("DROP TYPE baseitemsource_new"))

    op.alter_column("base_item", "range_long_meters", new_column_name="range_long")
    op.alter_column("base_item", "range_normal_meters", new_column_name="range_normal")
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET range_long = GREATEST(1, ROUND(range_long / 0.3048))
            WHERE range_long IS NOT NULL
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE base_item
            SET range_normal = GREATEST(1, ROUND(range_normal / 0.3048))
            WHERE range_normal IS NOT NULL
            """
        )
    )
