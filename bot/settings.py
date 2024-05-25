import yaml
from dataclasses import dataclass

BOT_ID = 7018368922


@dataclass
class Settings:
    api_id: int
    api_hash: str
    auto_upgrade: bool = True
    sleep_for_profitable: bool = True

    min_energy: int = 90
    min_taps: int = 50
    max_taps: int = 200
    min_sleep_time: int = 10
    max_sleep_time: int = 25


def read_settings() -> Settings:
    with open("settings.yaml") as file:
        settings_data = yaml.safe_load(file.read())
        if settings_data is None:
            raise RuntimeError("Settings file is empty or corrupted")

        return Settings(
            api_id=int(settings_data["api_id"]),
            api_hash=settings_data["api_hash"],
            auto_upgrade=bool(settings_data.get("auto_upgrade", True)),
            sleep_for_profitable=bool(settings_data.get("sleep_for_profitable", True)),
            min_energy=settings_data.get("min_energy", 90),
        )
