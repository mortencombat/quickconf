from pathlib import Path

from quickconf import Configuration


def test_void():
    conf = Configuration(Path("demo/settings.toml"))
    assert conf is not None, "This is a dummy test"
