from collections.abc import Iterable

import tomlkit
from tomlkit import nl, table
from tomlkit.container import Container

# doc.add("group",)
# doc["group"].add("subgroup")
# doc["group"]["subgroup"].add("setting", 5)
# doc["group"]["subgroup"]["setting"] = 5

data = """
title = "TOML Example"

[project.urls]
name = "Tom Preston-Werner"
organization = "GitHub"
bio = "GitHub Cofounder & CEO"
dob = 1979-05-27T07:32:00Z # First class dates? Why not?

[database]
server = "192.168.1.1"
ports = [ 8001, 8001, 8002 ]
connection_max = 5000
enabled = true
"""

doc = tomlkit.loads(data)


print(doc.as_string())


def add_setting(container: Container, keys: Iterable[str], value) -> None:
    n = len(keys)
    container.update()
    if keys[0] not in container:
        if n == 1:
            container.add(keys[0], value)
        else:
            t = table()
            t.add(keys[-1], value)
            container.add(".".join(keys[:-1]), t)
            container.add(nl())
    else:
        if n == 1:
            container[keys[0]] = value
        else:
            add_setting(container[keys[0]], keys[1:], value)


add_setting(doc, ("project", "urls", "homepage"), "google.com")
add_setting(doc, ("project", "urls", "subgroup", "repo"), "github.com")
add_setting(
    doc,
    (
        "new-table",
        "test-setting",
    ),
    5,
)

print(doc.as_string())
