from __future__ import annotations

import json
from pathlib import Path

from sqlmodel import Session, select

from app.api.serializers.base_spell import to_base_spell_seed_entry
from app.models.base_spell import BaseSpell
from app.schemas.base_spell import BaseSpellSeedDocument

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_SPELLS_SEED_PATH = REPO_ROOT / "Base" / "base_spells.seed.json"


def read_base_spell_seed_document(path: Path = DEFAULT_BASE_SPELLS_SEED_PATH) -> BaseSpellSeedDocument:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return BaseSpellSeedDocument.model_validate(payload)


def write_base_spell_seed_document(
    document: BaseSpellSeedDocument,
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized_document = BaseSpellSeedDocument(
        version=document.version,
        spells=sorted(
            document.spells,
            key=lambda spell: (
                spell.system.value,
                spell.level,
                spell.canonicalKey,
            ),
        ),
    )
    serialized = json.dumps(
        normalized_document.model_dump(mode="json", exclude_none=True),
        ensure_ascii=False,
        indent=2,
    )
    path.write_text(f"{serialized}\n", encoding="utf-8")


def export_base_spell_seed_document(
    db: Session,
    *,
    path: Path = DEFAULT_BASE_SPELLS_SEED_PATH,
) -> BaseSpellSeedDocument:
    spells = db.exec(
        select(BaseSpell).order_by(
            BaseSpell.system,
            BaseSpell.level,
            BaseSpell.canonical_key,
        )
    ).all()
    document = BaseSpellSeedDocument(
        version=1,
        spells=[to_base_spell_seed_entry(spell) for spell in spells],
    )
    write_base_spell_seed_document(document, path)
    return document
