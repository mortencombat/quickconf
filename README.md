[github_release]: https://img.shields.io/github/release/mortencombat/quickconf.svg?logo=github&logoColor=white
[pypi_version]: https://img.shields.io/pypi/v/quickconf.svg?logo=python&logoColor=white
[python_versions]: https://img.shields.io/pypi/pyversions/quickconf.svg?logo=python&logoColor=white
[github_license]: https://img.shields.io/github/license/mortencombat/quickconf.svg?logo=github&logoColor=white
[github_action]: https://github.com/mortencombat/quickconf/actions/workflows/tests.yml/badge.svg

[![GitHub Release][github_release]](https://github.com/mortencombat/quickconf/releases/)
[![PyPI Version][pypi_version]](https://pypi.org/project/quickconf/)
[![Python Versions][python_versions]](https://pypi.org/project/quickconf/)
[![License][github_license]](https://github.com/mortencombat/quickconf/blob/main/LICENSE)
<br>
[![Tests][github_action]](https://github.com/mortencombat/quickconf/actions/workflows/tests.yml)

# quickconf

Simple and flexible TOML-file based configurations framework

If [TOML Kit](https://pypi.org/project/tomlkit/) is installed, `quickconf` will use that and supports both reading and writing configuration files. If `tomlkit` is not available, `quickconf` will use the Python system library `tomllib` but will support only reading of configuration files.

Install `quickconf` with optional dependency `save` to ensure `tomlkit` is also installed: `pip install quickconf[save]`
