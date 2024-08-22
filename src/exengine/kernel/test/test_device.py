import pytest
from unittest.mock import MagicMock
from exengine.kernel.device import Device


@pytest.fixture
def mock_device():
    mock = MagicMock(spec=Device)
    # Explicitly add the methods we're testing
    mock.get_allowed_property_values = MagicMock(return_value=None)
    mock.is_property_read_only = MagicMock(return_value=False)
    mock.get_property_limits = MagicMock(return_value=(None, None))
    mock.is_property_hardware_triggerable = MagicMock(return_value=False)
    mock.get_triggerable_sequence_max_length = MagicMock(return_value=0)
    mock.load_triggerable_sequence = MagicMock()
    mock.start_triggerable_sequence = MagicMock()
    mock.stop_triggerable_sequence = MagicMock()
    return mock

def test_get_allowed_property_values(mock_device):
    mock_device.get_allowed_property_values.return_value = ['value1', 'value2']
    result = mock_device.get_allowed_property_values('test_property')
    assert result == ['value1', 'value2']

def test_is_property_read_only(mock_device):
    mock_device.is_property_read_only.return_value = True
    result = mock_device.is_property_read_only('test_property')
    assert result is True

def test_get_property_limits(mock_device):
    mock_device.get_property_limits.return_value = (0, 100)
    result = mock_device.get_property_limits('test_property')
    assert result == (0, 100)

def test_is_property_hardware_triggerable(mock_device):
    mock_device.is_property_hardware_triggerable.return_value = True
    result = mock_device.is_property_hardware_triggerable('test_property')
    assert result is True

def test_get_triggerable_sequence_max_length(mock_device):
    mock_device.get_triggerable_sequence_max_length.return_value = 1000
    result = mock_device.get_triggerable_sequence_max_length('test_property')
    assert result == 1000

def test_load_triggerable_sequence(mock_device):
    sequence = [1, 2, 3, 4, 5]
    mock_device.load_triggerable_sequence('test_property', sequence)
    mock_device.load_triggerable_sequence.assert_called_once_with('test_property', sequence)

def test_start_triggerable_sequence(mock_device):
    mock_device.start_triggerable_sequence('test_property')
    mock_device.start_triggerable_sequence.assert_called_once_with('test_property')

def test_stop_triggerable_sequence(mock_device):
    mock_device.stop_triggerable_sequence('test_property')
    mock_device.stop_triggerable_sequence.assert_called_once_with('test_property')

class TestDeviceDefaults:
    @pytest.fixture
    def default_device(self):
        return Device('default_device', no_executor=True)

    def test_get_allowed_property_values_default(self, default_device):
        assert default_device.get_allowed_property_values('test_property') is None

    def test_is_property_read_only_default(self, default_device):
        assert default_device.is_property_read_only('test_property') is False

    def test_get_property_limits_default(self, default_device):
        assert default_device.get_property_limits('test_property') == (None, None)

    def test_is_property_hardware_triggerable_default(self, default_device):
        assert default_device.is_property_hardware_triggerable('test_property') is False

    def test_get_triggerable_sequence_max_length_default(self, default_device):
        with pytest.raises(NotImplementedError):
            default_device.get_triggerable_sequence_max_length('test_property')

    def test_load_triggerable_sequence_default(self, default_device):
        with pytest.raises(NotImplementedError):
            default_device.load_triggerable_sequence('test_property', [1, 2, 3])

    def test_start_triggerable_sequence_default(self, default_device):
        with pytest.raises(NotImplementedError):
            default_device.start_triggerable_sequence('test_property')

    def test_stop_triggerable_sequence_default(self, default_device):
        with pytest.raises(NotImplementedError):
            default_device.stop_triggerable_sequence('test_property')