import pytest

# Import our custom_components package before the hass fixture gets a chance to import the one bundled with
# pytest-homeassistant-custom-component's testing config, otherwise the integration isn't found
import custom_components.extron  # noqa: F401

from tests.fake_extron import FakeExtron


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    return


@pytest.fixture
async def fake_extron(socket_enabled):
    device = FakeExtron()
    await device.start()
    yield device
    await device.stop()
