from core.config import config

def dump(name, value):
    print(f"\n=== {name} ===")
    print("repr:", repr(value))
    print("bytes:", value.encode("utf-8", errors="replace"))

dump("DB_USER", config.DB_USER)
dump("DB_PASSWORD", config.DB_PASSWORD)
dump("DB_HOST", config.DB_HOST)
dump("DB_PORT", config.DB_PORT)
dump("DB_NAME", config.DB_NAME)
