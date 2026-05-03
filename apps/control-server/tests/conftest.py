from unittest.mock import AsyncMock, patch

import pytest


@pytest.fixture(autouse=True)
def _mock_centrifugo():
    """Patch centrifugo.publish globally so tests never hit the real HTTP client."""
    mock = AsyncMock()
    with patch("app.services.combat_service.events.centrifugo", mock):
        yield mock
