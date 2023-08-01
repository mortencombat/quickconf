import re
from collections.abc import Iterable
from datetime import date, datetime, time
from enum import Flag, auto
from inspect import getmembers
from itertools import chain
from pathlib import Path
from typing import Any, Generic, TypeVar

try:
    import tomlkit as tomllib

    _USE_TOMLKIT = True
except ModuleNotFoundError:
    _USE_TOMLKIT = False
    try:
        import tomllib
    except ModuleNotFoundError:
        import tomli as tomllib

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

        value = config._get_value(self._keys, default=self._default)

        self._get_generic_type()
        if not isinstance(value, self._type):
            raise TypeError(
                f"{self.name} should be {self._type.__name__}, got '{value}' ({type(value).__name__})"
            )

        # TODO: Add validation support

        self._value = value
        self._loaded = True

    def _dump(self, config: "Configuration", value: T) -> None:
        if not self._loaded:
            self._get_generic_type()

        if not isinstance(value, self._type):
            raise TypeError(
                f"{self.name} should be {self._type.__name__}, got '{value}' ({type(value).__name__})"
            )

        # TODO: Check validation

        config._set_value(self._keys, value)

    def __get__(self, instance: "Configuration", owner: "Configuration" = None) -> T:
        if not instance:
            return self
        if not self._loaded:
            self._load(instance)
        return self._value

    def __set__(self, instance: "Configuration", value: T) -> None:
        if not instance or instance.is_readonly:
            raise AttributeError(self.name)
        self._dump(instance, value)
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
        if setting.name not in self._settings:
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
        self._settings = {}

    def __contains__(self, name: str) -> bool:
        return name in self._settings

    def __getitem__(self, name: str) -> Setting:
        if name not in self._settings:
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

        # NOTE! There could be name clashes with the current implementation, both in Configuration and in _Proxy,
        #       if a settings key has the same name as a class attribute
        #       Raise an error if ATTR access is enabled and a setting is defined or loaded that clashes with a class attribute/method.

        def __getattr__(self, key: str):
            if key in ("_config", "_name"):
                raise AttributeError(key)

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

        def __setattr__(self, key: str, value: str) -> None:
            if key in ("_config", "_name"):
                return super().__setattr__(key, value)

            setting = f"{self._name}.{key}"
            if setting in self._config._settings:
                return self._config.settings[setting].__set__(self._config, value)
            elif (
                not self._config._defined_only
                and setting in self._config._settings_flex
            ):
                return self._config._settings_flex[setting].__set__(self._config, value)
            raise AttributeError(setting)

    def __init__(
        self,
        config: Path | str | dict = None,
        *,
        settings: Settings | Iterable[Setting] = None,
        defined_only: bool = False,
        access: SettingsAccess = SettingsAccess.ANY,
        allow_changes: bool = True,
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
        self._allow_changes = allow_changes

        # Assemble options from arg and class attributes.
        self._settings = Settings(settings)
        self._settings_flex = Settings()
        for _, obj in getmembers(type(self)):
            if not isinstance(obj, Setting):
                continue
            self._settings.append(obj)
        self.__TYPE_MAP = None

        # Load configuration
        self.load(config)

    def __get_base_type(self, cls) -> type:
        if _USE_TOMLKIT:
            if not self.__TYPE_MAP:
                self.__TYPE_MAP = {
                    tomllib.items.Float: float,
                    tomllib.items.Integer: int,
                    tomllib.items.String: str,
                    tomllib.items.DateTime: datetime,
                    tomllib.items.Date: date,
                    tomllib.items.Time: time,
                    tomllib.items.Bool: bool,
                }
            if cls in self.__TYPE_MAP:
                return self.__TYPE_MAP[cls]
            raise TypeError(cls)
        else:
            return cls

    def reset(self) -> None:
        """Resets all settings to their default values."""
        for setting in self._settings:
            del setting
        self._settings_flex.clear()
        self._data = {}

    def load(self, config: Path | str | dict = None) -> None:
        self.reset()
        if config is None:
            return
        if isinstance(config, dict):
            self._load_dict(config)
        else:
            self._load_toml(config)

    def save(self, path: Path | str) -> None:
        if self.is_readonly:
            raise OSError("Configuration is read-only")
        with open(path, "w") as f:
            f.write(tomllib.dumps(self._data))

    def _has_section(self, section: str) -> bool:
        s = section + "."
        return any(
            setting.name.startswith(s)
            for setting in chain(self._settings, self._settings_flex)
        )

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
        r = {}
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
                if setting not in self._settings:
                    self._settings_flex.append(
                        Setting[self.__get_base_type(type(value))](setting)
                    )

    @property
    def is_readonly(self) -> bool:
        return not _USE_TOMLKIT or not self._allow_changes

    @property
    def settings(self) -> dict[str, Any]:
        r = {}
        for s in chain(self._settings, self._settings_flex):
            r[s.name] = s.__get__(self)
        return dict(sorted(r.items()))

    def _get_value(self, keys: tuple[str], default: Any = None) -> Any:
        try:
            return self.__get_value(self._data, keys, 0)
        except KeyError as e:
            if default is not None:
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

    def _set_value(self, keys: tuple[str], value: T) -> None:
        Configuration.__set_value(self._data, keys, value)

    @staticmethod
    def __set_value(container, keys: tuple[str], value: T) -> None:
        n = len(keys)
        container.update()
        if keys[0] not in container:
            if n == 1:
                container.add(keys[0], value)
            else:
                t = tomllib.table()
                t.add(keys[-1], value)
                container.add(".".join(keys[:-1]), t)
                container.add(tomllib.nl())
        else:
            if n == 1:
                container[keys[0]] = value
            else:
                Configuration.__set_value(container[keys[0]], keys[1:], value)

    def __getattr__(self, name: str) -> Any:
        if name in (
            "_defined_only",
            "_access",
            "_allow_changes",
            "_settings",
            "_settings_flex",
            "_data",
        ):
            raise AttributeError(name)

        if Configuration.SettingsAccess.ATTR in self._access:
            if name in self._settings:
                return self._settings[name]
            elif not self._defined_only and name in self._settings_flex:
                return self._settings_flex[name]
            elif self._has_section(name):
                return Configuration._Proxy(self, name)
        raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        if name in (
            "_defined_only",
            "_access",
            "_allow_changes",
            "_settings",
            "_settings_flex",
            "_data",
        ):
            return super().__setattr__(name, value)

        if Configuration.SettingsAccess.ATTR in self._access:
            if name in self._settings:
                self._settings[name] = value
                return
            elif not self._defined_only and name in self._settings_flex:
                self._settings_flex[name] = value
                return
        super().__setattr__(name, value)

    def __getitem__(self, name: str) -> Any:
        if Configuration.SettingsAccess.ITEM in self._access:
            if name in self._settings:
                return self._settings[name].__get__(self)
            elif not self._defined_only and name in self._settings_flex:
                return self._settings_flex[name].__get__(self)
        raise KeyError(name)

    def __setitem__(self, name: str, value: Any) -> None:
        if Configuration.SettingsAccess.ITEM in self._access:
            if name in self._settings:
                return self._settings[name].__set__(self, value)
            elif not self._defined_only and name in self._settings_flex:
                return self._settings_flex[name].__set__(self, value)
        raise KeyError(name)
