import tomllib

with open("demo/settings.toml", "rb") as f:
    doc = tomllib.load(f)

p = doc["layout"]["point"]["size"]
print(p)
print(type(p))
