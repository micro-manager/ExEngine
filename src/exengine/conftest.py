import os
import pytest
from mmpycorex import (download_and_install_mm, find_existing_mm_install, create_core_instance,
                       terminate_core_instances, get_default_install_location)

@pytest.fixture(scope="session")
def install_mm():
    if find_existing_mm_install():
        print('Micro-Manager is already installed, skipping installation')
        yield find_existing_mm_install()
    else:
        # Download an install latest nightly build
        mm_install_dir = download_and_install_mm(destination='auto')

        yield mm_install_dir


@pytest.fixture(scope="session")
def launch_micromanager(install_mm):
    mm_install_dir = get_default_install_location()
    config_file = os.path.join(mm_install_dir, 'MMConfig_demo.cfg')
    create_core_instance(mm_install_dir, config_file,
                   buffer_size_mb=1024, max_memory_mb=1024,  # set these low for github actions
                   python_backend=True,
                   debug=False)
    yield
    terminate_core_instances()
