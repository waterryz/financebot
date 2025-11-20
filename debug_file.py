import pathlib

files = [
    "core/config.py",
    "database/models.py"
]

for f in files:
    print("\n=== CHECKING:", f, "===")
    data = pathlib.Path(f).read_bytes()
    print("Length:", len(data))
    print("Byte dump (C2 highlighted):")
    print([hex(b) for b in data])
