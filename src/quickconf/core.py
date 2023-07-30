import tomllib
from enum import Flag, auto
from pathlib import Path
from typing import Any, Generic, Iterable, TypeVar

T = TypeVar("T")


class Option(Generic[T]):
    # NOTE: This is a 'descriptor class', similar to using property()
    # https://docs.python.org/3/reference/datamodel.html?highlight=__get__#implementing-descriptors

    def __init__(self, name: str, *, default: T = None, doc: str = None) -> None:
        super().__init__()
        self._name = name
        self._default = default
        self._loaded = False
        self._value = None
        self._type = None
        self.__doc__ = doc

    # TODO: implement name validator, does tomllib have a method we can use?

    @property
    def name(self) -> str:
        return self._name

    def _get_generic_type(self) -> None:
        self._type = self.__orig_class__.__args__[0]

    def _load(self, config: "Configuration") -> None:
        # Retrieve value from config
        # Perform type-checking, validation, etc. and assign default if applicable.
        if not self._type:
            self._get_generic_type()
        raise NotImplementedError

    def __get__(self, instance: "Configuration", owner: "Configuration" = None) -> T:
        if not instance:
            raise AttributeError(f"Option {self._name} must be an instance attribute")
        if not self._loaded:
            self._load(instance)
        return self._value

    def __set__(self, instance: "Configuration", value: T) -> None:
        # TODO: Check if instance is set to read-only (immutable) or read/write
        # Raise AttributeError if read-only.
        self._value = value

    def __hash__(self) -> int:
        return self._name


class Options:
    def __init__(self, options: Iterable[Option] = None):
        self._options = dict()
        if options:
            self.extend(options)

    def append(self, option: Option) -> bool:
        if not option.name in self._options:
            self._options[option.name] = option
            return True
        else:
            return False

    def extend(self, options: Iterable[Option]) -> int:
        n = 0
        for option in options:
            if self.append(option):
                n += 1
        return n

    def __getitem__(self, name: str) -> Option:
        if not name in self._options:
            raise KeyError(f"Option '{name}' not found")
        return self._options[name]

    # TODO: Implement Iterable support, iterating over values
    #       (like a List on the values)


class Configuration:
    class OptionAccess(Flag):
        ATTRIBUTE_EXPLICIT = auto()  # Defined directly on class, by subclassing
        ATTRIBUTE = auto()  # Automatically supported, using __getattr__
        INDEX = auto()  # Automatically supported, using __getitem__
        ANY = ATTRIBUTE_EXPLICIT | ATTRIBUTE | INDEX

    def __init__(
        self,
        config: Path | str | dict = None,
        *,
        options: Options | Iterable[Option] = None,
        defined_only: bool = False,
        access: OptionAccess = OptionAccess.ANY,
    ) -> None:
        """Returns a Configuration instance.

        :param config: If a valid path (Path or str), load config from file (toml-format). If a dict, load config from dict. If a str (not filepath), attempt to parse as toml., defaults to None
        :type config: Path | dict[str, object], optional

        If config is None, check for env var MAGNETIC_CONFIG for filepath.
        If config is a filepath, read configuration from that file (toml format).
        If config is a dict, read configuration from dict.
        If none of the above, configuration will use all defaults.
        """

        # Assemble options from arg and class attributes.
        # NOTE: We create a new Options (eg. clone it) even if the arg is already
        #       an Options instance.
        self._options = Options(options)

        # TODO: look at class attributes to find additional options

        pass

    def read_toml() -> None:
        pass

    def read_dict() -> None:
        pass

    def __getattr__(self, name: str) -> Any:
        pass

    def __getitem__(self, name: str) -> Any:
        pass
