"""
This class tests the access of micro-manager properties through the MicroManagerDevice class.
"""
import pytest
from mmpycorex import Core
import os
from mmpycorex import create_core_instance, terminate_core_instances, get_default_install_location
from exengine.kernel.executor import ExecutionEngine
from exengine.backends.micromanager.mm_device_implementations import MicroManagerDevice



@pytest.fixture(scope="module")
def executor():
    executor = ExecutionEngine()
    yield executor
    executor.shutdown()

@pytest.fixture(scope="module")
def device(launch_micromanager, executor):
    return MicroManagerDevice("Camera")


def test_init(device):
    assert isinstance(device, MicroManagerDevice)
    assert device._name == "Camera"


def test_getattr_existing_property(device):
    assert device.Binning == "1"


def test_getattr_non_existing_property(device):
    with pytest.raises(AttributeError):
        _ = device.NonExistentProperty


def test_setattr_writable_property(device):
    original_value = device.Binning
    new_value = "2" if original_value != "2" else "1"
    device.Binning = new_value
    assert device.Binning == new_value
    # Reset to original value
    device.Binning = original_value


def est_setattr_readonly_property(device):
    with pytest.raises(ValueError):
        device.Description = "You cant change this"


def test_setattr_non_existing_property(device):
    with pytest.raises(AttributeError):
        device.NonExistentProperty = "some_value"


def test_dir(device):
    dir_result = dir(device)
    assert "Binning" in dir_result
    assert "Exposure" in dir_result
    assert "PixelType" in dir_result


def test_get_allowed_property_values(device):
    allowed_values = device.get_allowed_property_values("Binning")
    assert allowed_values == ('1', '2', '4', '8')


@pytest.mark.parametrize("property_name, expected", [
    ("Binning", False),
    ("CCDTemperature RO", True)
])
def test_is_property_read_only(device, property_name, expected):
    assert device.is_property_read_only(property_name) == expected


def test_is_property_hardware_triggerable(device):
    assert not device.is_property_hardware_triggerable("Binning")

def test_get_triggerable_sequence_max_length(device):
    # Since no property is sequenceable for the Camera, we expect this to raise an exception
    with pytest.raises(Exception):  # You might want to define a more specific exception
        device.get_triggerable_sequence_max_length("Binning")


def test_get_property_limits(device):
    limits = device.get_property_limits("Exposure")
    assert limits == (0.0, 10000.0)


def test_load_triggerable_sequence(device):
    # Since no property is sequenceable for the Camera, we expect this to raise an exception
    with pytest.raises(Exception):  # You might want to define a more specific exception
        device.load_triggerable_sequence("Binning", ["1", "2", "4"])


def test_start_triggerable_sequence(device):
    # Since no property is sequenceable for the Camera, we expect this to raise an exception
    with pytest.raises(Exception):  # You might want to define a more specific exception
        device.start_triggerable_sequence("Binning")


def test_stop_triggerable_sequence(device):
    # Since no property is sequenceable for the Camera, we expect this to raise an exception
    with pytest.raises(Exception):  # You might want to define a more specific exception
        device.stop_triggerable_sequence("Binning")


# Additional test for a sequenceable property (using the Objective device)
@pytest.fixture(scope="module")
def objective_device(launch_micromanager, executor):
    return MicroManagerDevice("Objective")

def test_is_property_hardware_triggerable(objective_device):
    assert objective_device.is_property_hardware_triggerable("Label")

def test_sequenceable_property(objective_device):
    assert objective_device.is_property_hardware_triggerable("Label")
    assert objective_device.get_triggerable_sequence_max_length("Label") == 10

    # Test loading a sequence
    objective_device.load_triggerable_sequence("Label", ["Nikon 10X S Fluor", "Nikon 20X Plan Fluor ELWD"])

    # Start and stop the sequence
    objective_device.start_triggerable_sequence("Label")
    objective_device.stop_triggerable_sequence("Label")