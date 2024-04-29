import json


class ConfigManager:
    def __init__(self, filename="config.json"):
        self.filename = filename
        self.config = self._load_config()

    def get(self, key):
        return self.config.get(key)

    def set(self, key, value):
        self.config[key] = value
        self._save_config()

    def _load_config(self):
        try:
            with open(self.filename, "r") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_config(self):
        with open(self.filename, "w") as f:
            json.dump(self.config, f)

