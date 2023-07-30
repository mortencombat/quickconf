from pathlib import Path

from quickconf import Configuration, Option, Options

options = Options(
    (
        Option[int]("layout.resolution", default=100),
        Option[float]("layout.point.size", default=0.1),
        Option[int]("page.dpi", default=150),
        Option[int]("page.margins", default=10),
    )
)


class ExampleConfig(Configuration):
    layout_resolution: int = options["layout.resolution"]
    layout_point_size: float = options["layout.point.size"]
    page_dpi: int = options["page.dpi"]
    page_margins: int = options["page.margins"]


data = Path("demo/settings.toml")

# Settings are defined explicitly by subclassing Configuration.
# The settings are available as attributes (properties), includes autocomplete and typing.
# Settings are only available as the explicitly defined class attributes of ExampleConfig,
# fx. conf_subcl.layout_point_size
conf_subcl = ExampleConfig(
    data, defined_only=True, access=Configuration.OptionAccess.ATTRIBUTE_EXPLICIT
)

# Settings are inferred from the configuration file, eg. all settings from the file are read.
# Settings are only available using eg. conf_impl.layout.point.size
conf_impl = Configuration(data, access=Configuration.OptionAccess.ATTRIBUTE)

# Settings are defined in options. Any settings in data that are not explicitly defined are
# ignored. Settings are only available using eg. conf_expl["layout.point.size"]
conf_expl = Configuration(
    data, options=options, defined_only=True, access=Configuration.OptionAccess.INDEX
)
