import json

from leap.shared.config import load_json_config


def test_load_json_config(tmp_path) -> None:
    path = tmp_path / "config.json"
    path.write_text(json.dumps({"seed": 42}), encoding="utf-8")
    assert load_json_config(path) == {"seed": 42}
