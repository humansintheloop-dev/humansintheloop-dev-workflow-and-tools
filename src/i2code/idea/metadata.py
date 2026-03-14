from pathlib import Path

import yaml


def read_metadata(path: Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f)


def write_metadata(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False)
