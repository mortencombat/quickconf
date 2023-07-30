from pathlib import Path

from quickconf import Configuration, Setting, Settings

"""
This example demonstrates the three basic ways quickconf can be used, in terms of loading and accessing settings.
The access methods can also be used concurrently, which is the default allowed behaviour.

Each of the three examples demonstrates both the different settings access methods as well as the available settings.
"""

settings = Settings(
    (
        Setting[int]("layout.resolution", default=100),
        Setting[float]("layout.point.size", default=0.1),
        Setting[int]("page.dpi", default=150),
        Setting[int]("page.margins", default=10),
    )
)


class ExampleConfig(Configuration):
    layout_resolution: int = settings["layout.resolution"]
    layout_point_size: float = settings["layout.point.size"]
    page_dpi: int = settings["page.dpi"]
    page_margins: int = settings["page.margins"]


data = Path("demo/settings.toml")

# Settings are defined explicitly by subclassing Configuration.
# The settings are available as attributes (properties), includes autocomplete and typing.
# Settings are only available as the explicitly defined class attributes of ExampleConfig,
# fx. conf_subcl.layout_point_size
print("\nEXAMPLE 1: subclassed Configuration with explicit attributes")
config = ExampleConfig(
    data, defined_only=True, access=Configuration.SettingsAccess.ATTR_EXPLICIT
)
print(f"{config.layout_point_size=}")
for setting, value in config.settings.items():
    print(f"{setting} = {value}")

# Settings are inferred from the configuration file, eg. all settings from the file are read.
# Settings are only available using eg. conf_impl.layout.point.size
print("\nEXAMPLE 2: Configuration with all settings in .toml file and attribute access")
config = Configuration(data, access=Configuration.SettingsAccess.ATTR)
print(f"{config.layout.point.size=}")
for setting, value in config.settings.items():
    print(f"{setting} = {value}")

# Settings are defined in options. Any settings in data that are not explicitly defined are
# ignored. Settings are only available using eg. conf_expl["layout.point.size"]
print("\nEXAMPLE 3: Configuration with only defined settings and item access [...]")
config = Configuration(
    data, settings=settings, defined_only=True, access=Configuration.SettingsAccess.ITEM
)
print(f"{config['layout.point.size']=}")
for setting, value in config.settings.items():
    print(f"{setting} = {value}")
