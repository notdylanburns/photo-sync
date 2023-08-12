import abc
import os
import re
import yaml


class Config(abc.ABC):
    def __init__(self, filepath: str):
        self.filepath = filepath
        self._assert(os.path.exists(filepath), "file not found")

        try:
            with open(filepath, "rt") as f:
                self.configuration = yaml.safe_load(f)
                self.parse_configuration(self.configuration)
        except yaml.YAMLError as e:
            self._assert(False, f"invalid YAML: {e}")

    def _assert(self, condition: bool, message: str):
        if not condition:
            print(f"error while parsing '{self.filepath}': {message}")
            exit(1)
    
    def assert_present(self, configuration: dict, *keys, parent_keys=[]):
        for key in keys:
            self._assert(
                key in configuration,
                f"required key '{'.'.join([*parent_keys, key])}' missing"
            )

    def assert_type(self, configuration: dict, type: type, *keys, parent_keys=[]):
        for key in keys:
            self._assert(
                isinstance(configuration[key], type),
                f"key '{'.'.join([*parent_keys, key])}' must have type '{type.__name__}'"
            )

    @abc.abstractmethod
    def parse_configuration(self, configuration: dict): ...
