from __future__ import annotations

from pydantic import BaseModel, model_validator

from .base_spell_effects import SpellDeclarativeEffect


class SpellVariantManualNote(BaseModel):
    key: str
    label: str
    description: str

    @model_validator(mode="after")
    def validate_text_fields(self):
        self.key = self.key.strip()
        self.label = self.label.strip()
        self.description = self.description.strip()
        if not self.key:
            raise ValueError("Spell variant manual note key cannot be blank.")
        if not self.label:
            raise ValueError("Spell variant manual note label cannot be blank.")
        if not self.description:
            raise ValueError("Spell variant manual note description cannot be blank.")
        return self


class SpellVariant(BaseModel):
    key: str
    labelEn: str | None = None
    labelPt: str
    descriptionEn: str | None = None
    descriptionPt: str | None = None
    effects: list[SpellDeclarativeEffect] | None = None
    onEndEffects: list[SpellDeclarativeEffect] | None = None
    manualNotes: list[SpellVariantManualNote] | None = None

    @model_validator(mode="after")
    def validate_variant(self):
        self.key = self.key.strip()
        self.labelPt = self.labelPt.strip()
        self.labelEn = self.labelEn.strip() if isinstance(self.labelEn, str) else None
        self.descriptionEn = (
            self.descriptionEn.strip() if isinstance(self.descriptionEn, str) else None
        )
        self.descriptionPt = (
            self.descriptionPt.strip() if isinstance(self.descriptionPt, str) else None
        )
        if not self.key:
            raise ValueError("Spell variant key cannot be blank.")
        if not self.labelPt:
            raise ValueError("Spell variant labelPt cannot be blank.")
        if self.onEndEffects and not self.effects:
            raise ValueError("Spell variant onEndEffects requires effects to be present.")
        return self


class SpellVariantSummary(BaseModel):
    key: str
    label: str
    description: str | None = None
    manualNotes: list[SpellVariantManualNote] | None = None
