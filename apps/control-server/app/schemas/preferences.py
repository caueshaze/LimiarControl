from typing import Optional

from pydantic import BaseModel


class PreferencesRead(BaseModel):
    selectedCampaignId: Optional[str]


class PreferencesUpdate(BaseModel):
    selectedCampaignId: Optional[str] = None
