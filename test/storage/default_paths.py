# pyright: strict

"""
The paths `Defaults` derives from a `MockPathService` with the default home dir.
"""

from test.system.mock_path_service import DEFAULT_HOME_DIR


DEFAULT_CONFIG_DIR = f'{DEFAULT_HOME_DIR}/.config/system-config-manager'
DEFAULT_OLD_CONFIG_PATH = f'{DEFAULT_CONFIG_DIR}/.history/current.yaml'
DEFAULT_CONFIG_LOCATION_PATH = f'{DEFAULT_CONFIG_DIR}/config'
DEFAULT_NEW_CONFIG_PATH = f'{DEFAULT_CONFIG_LOCATION_PATH}/config.yaml'
