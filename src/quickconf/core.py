import re
from enum import Flag, auto
from inspect import getmembers
from itertools import chain
from pathlib import Path
from typing import Any, Generic, Iterable, TypeVar

try:
    import tomlkit as tomllib
except ModuleNotFoundError:
    import tomllib

T = TypeVar("T")

_key_pattern = re.compile("[A-Za-z0-9_-]+")


def parse_key(key: str) -> tuple[str]:
    keys = key.split(".")
    for k in keys:
        if not _key_pattern.match(k):
            raise ValueError(
                f"{key} is invalid/unsupported. Only bare TOML keys are supported."
            )
    return tuple(keys)


class Setting(Generic[T]):
    # NOTE: This is a 'descriptor class', similar to using property()
    # https://docs.python.org/3/reference/datamodel.html?highlight=__get__#implementing-descriptors

    def __init__(self, name: str, *, default: T = None, doc: str = None) -> None:
        super().__init__()

        self._name = name.replace(" ", "")
        self._keys = parse_key(self._name)
        self._default = default
        self._type = None
        self.__doc__ = doc
        self._reset()

    # TODO: implement name validator, does tomllib have a method we can use?

    # Add support for validators, and a couple of stock validators

    @property
    def name(self) -> str:
        return self._name

    def _reset(self) -> None:
        self._value = None
        self._loaded = False

    def _get_generic_type(self) -> None:
        self._type = self.__orig_class__.__args__[0]

    def _load(self, config: "Configuration") -> None:
        """Retrieves settings value from configuration"""

        v = config._get_value(self._keys, default=self._default)

        self._get_generic_type()
        if not isinstance(v, self._type):
            raise TypeError(
                f"{self.name} should be {self._type.__name__}, got '{v}' ({type(v).__name__})"
            )

        # TODO: Add validation support

        self._value = v
        self._loaded = True

    def _dump(self, config: "Configuration") -> None:
        raise NotImplementedError

    def __get__(self, instance: "Configuration", owner: "Configuration" = None) -> T:
        if not instance:
            return self
        if not self._loaded:
            self._load(instance)
        return self._value

    def __set__(self, instance: "Configuration", value: T) -> None:
        if not instance or instance._read_only:
            raise AttributeError(self.name)
        self._value = value

    def __delete__(self, instance: "Configuration") -> None:
        self._reset()

    def __hash__(self) -> int:
        return self._name


class Settings:
    def __init__(self, settings: Iterable[Setting] = None):
        self.clear()
        if settings:
            self.extend(settings)

    def append(self, setting: Setting) -> bool:
        if not setting.name in self._settings:
            self._settings[setting.name] = setting
            return True
        else:
            return False

    def extend(self, settings: Iterable[Setting]) -> int:
        n = 0
        for setting in settings:
            if self.append(setting):
                n += 1
        return n

    def clear(self) -> None:
        self._settings = dict()

    def __contains__(self, name: str) -> bool:
        return name in self._settings

    def __getitem__(self, name: str) -> Setting:
        if not name in self._settings:
            raise KeyError(name)
        return self._settings[name]

    def __iter__(self):
        return iter(self._settings.values())


class Configuration:
    class SettingsAccess(Flag):
        ATTR_EXPLICIT = auto()  # Defined directly on class, by subclassing
        ATTR = auto()  # Automatically supported, using __getattr__
        ITEM = auto()  # Automatically supported, using __getitem__
        ANY = ATTR_EXPLICIT | ATTR | ITEM

    class _Proxy:
        def __init__(self, config: "Configuration", name: str):
            self._config = config
            self._name = name

        def __getattr__(self, key: str):
            setting = f"{self._name}.{key}"
            if setting in self._config._settings:
                return self._config.settings[setting].__get__(self._config)
            elif (
                not self._config._defined_only
                and setting in self._config._settings_flex
            ):
                return self._config._settings_flex[setting].__get__(self._config)
            if not self._config._has_section(setting):
                raise AttributeError(setting)

            return Configuration._Proxy(self._config, setting)

    def __init__(
        self,
        config: Path | str | dict = None,
        *,
        settings: Settings | Iterable[Setting] = None,
        defined_only: bool = False,
        access: SettingsAccess = SettingsAccess.ANY,
    ) -> None:
        """Returns a Configuration instance.

        :param config: If a valid path (Path or str), load config from file (toml-format). If a dict, load config from dict. If a str (not filepath), attempt to parse as toml., defaults to None
        :type config: Path | dict[str, object], optional

        If config is a filepath, read configuration from that file (toml format).
        If config is a dict, read configuration from dict.
        If none of the above, configuration will use all defaults.
        """

        # Misc. config
        self._defined_only = defined_only
        self._access = access
        self._read_only = True  # Only read-only supported at the moment

        # Assemble options from arg and class attributes.
        self._settings = Settings(settings)
        self._settings_flex = Settings()
        for _, obj in getmembers(type(self)):
            if not isinstance(obj, Setting):
                continue
            self._settings.append(obj)

        # Load configuration
        self.load(config)

    def reset(self) -> None:
        """Resets all settings to their default values."""
        for setting in self._settings:
            del setting
        self._settings_flex.clear()

    def load(self, config: Path | str | dict = None) -> None:
        self.reset()
        if config is None:
            return
        if isinstance(config, dict):
            self._load_dict(config)
        else:
            self._load_toml(config)

    def _has_section(self, section: str) -> bool:
        s = section + "."
        for setting in chain(self._settings, self._settings_flex):
            if setting.name.startswith(s):
                return True
        return False

    def _load_toml(self, config: Path | str) -> None:
        """Load configuration settings from a path pointing to a toml-file or
        directly from a toml-formatted string."""
        try:
            with open(config, "rb") as f:
                data = tomllib.load(f)
        except OSError:
            data = tomllib.loads(config)
        return self._load_dict(data)

    @staticmethod
    def _get_settings_from_dict(data: dict, section: str = None) -> dict:
        r = dict()
        for name, value in data.items():
            s = f"{section}.{name}" if section else name
            if isinstance(value, dict):
                r.update(Configuration._get_settings_from_dict(data[name], s))
            else:
                r[s] = value
        return r

    def _load_dict(self, config: dict) -> None:
        """Load configuration settings from a dict."""
        self.reset()
        self._data = config
        if not self._defined_only:
            # Add settings to self._settings_flex for each item in self._data,
            # unless it is already defined in self._settings
            for setting, value in self._get_settings_from_dict(config).items():
                if not setting in self._settings:
                    self._settings_flex.append(Setting[type(value)](setting))

    @property
    def settings(self) -> dict[str, Any]:
        r = dict()
        for s in chain(self._settings, self._settings_flex):
            r[s.name] = s.__get__(self)
        return dict(sorted(r.items()))

    def _get_value(self, keys: tuple[str], default: Any = None) -> Any:
        try:
            return self.__get_value(self._data, keys, 0)
        except KeyError as e:
            if not default is None:
                return default
            raise e

    @staticmethod
    def __get_value(data: dict, keys: tuple[str], level: int) -> Any:
        if not keys[level] in data:
            raise KeyError(".".join(keys))
        return (
            Configuration.__get_value(data[keys[level]], keys, level + 1)
            if level + 1 < len(keys)
            else data[keys[level]]
        )

    def __getattr__(self, name: str) -> Any:
        if not Configuration.SettingsAccess.ATTR in self._access:
            raise AttributeError(name)
        if name in self._settings:
            return self._settings[name]
        if not self._has_section(name):
            raise AttributeError(name)

        return Configuration._Proxy(self, name)

    def __getitem__(self, name: str) -> Any:
        if (
            not Configuration.SettingsAccess.ITEM in self._access
            or not name in self._settings
        ):
            raise KeyError(name)
        return self._settings[name].__get__(self)
