
from pycromanager import Core


def read_mm_config_groups():
    """
    Read all Micro-Manager config groups and their associated properties (excluding core properties) and return as a
    dictionary of dictionaries. The outer dictionary has config group names as keys and the inner dictionaries have
    config names as keys and a dictionary of device properties as values.
    """
    core = Core()

    all_configs = {}
    config_groups = core.get_available_config_groups()
    # Iterate through each config group
    for group in config_groups:
        # Get configs in this group
        configs = core.get_available_configs(group)

        group_configs = {}

        # Get data for each config
        for config in configs:
            config_data = core.get_config_data(group, config)

            # Extract settings from config data
            settings = {}
            for i in range(config_data.size()):
                setting = config_data.getSetting(i)
                device = setting.getDeviceLabel()
                if device == "Core":
                    continue  # Ignore core properties
                prop = setting.getPropertyName()
                value = setting.getPropertyValue()

                if device not in settings:
                    settings[device] = {}
                settings[device][prop] = value

            group_configs[config] = settings

        all_configs[group] = group_configs
        return all_configs

