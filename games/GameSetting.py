from collections import namedtuple


class GameSetting:
    def __init__(self, display, setting_type, default, validator=lambda new_val: True):
        self.validator = validator
        self.default = default
        self.setting_type = setting_type
        self.display = display
