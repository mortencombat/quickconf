# quickconf

Simple and flexible TOML-file based configurations framework

If [TOML Kit](https://pypi.org/project/tomlkit/) is installed, `quickconf` will use that and supports both reading and writing configuration files. If `tomlkit` is not available, `quickconf` will use the Python system library `tomllib` but will support only reading of configuration files.

Install `quickconf` with optional dependency `save` to ensure `tomlkit` is also installed: `pip install quickconf[save]`
