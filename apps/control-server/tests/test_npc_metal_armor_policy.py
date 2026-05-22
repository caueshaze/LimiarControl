from __future__ import annotations

import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.models.campaign_entity import CampaignEntity
from app.models.session_entity import SessionEntity
from app.schemas.campaign_entity import CampaignEntityCreate
from app.schemas.combat import CombatParticipant, CombatStartRequest
from app.services.combat import CombatService


class NpcMetalArmorSchemaTests(unittest.TestCase):
    def test_campaign_entity_accepts_true_false_and_null(self):
        with_true = CampaignEntityCreate(name="Knight", wearingMetalArmor=True)
        with_false = CampaignEntityCreate(name="Scout", wearingMetalArmor=False)
        without_value = CampaignEntityCreate(name="Mystery")

        self.assertIs(with_true.wearingMetalArmor, True)
        self.assertIs(with_false.wearingMetalArmor, False)
        self.assertIsNone(without_value.wearingMetalArmor)


class NpcMetalArmorCombatSnapshotTests(unittest.IsolatedAsyncioTestCase):
    @patch("app.services.combat.CombatService._emit_state", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._emit_log", new_callable=AsyncMock)
    @patch("app.services.combat.CombatService._sync_all_participant_statuses")
    @patch("app.services.combat.CombatService._resolve_map_selection", return_value=None)
    @patch("app.services.combat.CombatService.get_state", return_value=None)
    async def test_start_combat_propagates_true_false_and_null_without_inference(
        self,
        _mock_get_state,
        _mock_resolve_map_selection,
        _mock_sync_status,
        _mock_emit_log,
        _mock_emit_state,
    ):
        db = MagicMock()
        db.exec.side_effect = [
            MagicMock(first=MagicMock(return_value=SessionEntity(id="se-true", session_id="session-1", campaign_entity_id="ce-true"))),
            MagicMock(first=MagicMock(return_value=CampaignEntity(id="ce-true", campaign_id="camp-1", name="Knight", armor_class=18, wearing_metal_armor=True))),
            MagicMock(first=MagicMock(return_value=SessionEntity(id="se-false", session_id="session-1", campaign_entity_id="ce-false"))),
            MagicMock(first=MagicMock(return_value=CampaignEntity(id="ce-false", campaign_id="camp-1", name="Scout", armor_class=12, wearing_metal_armor=False))),
            MagicMock(first=MagicMock(return_value=SessionEntity(id="se-null", session_id="session-1", campaign_entity_id="ce-null"))),
            MagicMock(first=MagicMock(return_value=CampaignEntity(id="ce-null", campaign_id="camp-1", name="Mystery Armor 18", armor_class=18, description="Wears plate armor", wearing_metal_armor=None))),
        ]

        req = CombatStartRequest(
            participants=[
                CombatParticipant(id="p1", kind="session_entity", ref_id="se-true", display_name="Knight", team="enemies"),
                CombatParticipant(id="p2", kind="session_entity", ref_id="se-false", display_name="Scout", team="enemies"),
                CombatParticipant(id="p3", kind="session_entity", ref_id="se-null", display_name="Mystery Armor 18", team="enemies"),
            ],
            useMap=False,
        )

        state = await CombatService.start_combat(db, "session-1", req)
        by_ref = {p["ref_id"]: p for p in state.participants}

        self.assertIs(by_ref["se-true"].get("wearingMetalArmor"), True)
        self.assertIs(by_ref["se-false"].get("wearingMetalArmor"), False)
        self.assertIsNone(by_ref["se-null"].get("wearingMetalArmor"))


if __name__ == "__main__":
    unittest.main()
