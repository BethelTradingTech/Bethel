from main import app
schema = app.openapi()
print("=" * 100)
print("BETHEL TRADING TECHNOLOGIES - REGISTERED API ROUTES")
print("=" * 100)
allowed = {"get", "post", "put", "patch", "delete", "options", "head"}
for path, operations in sorted(schema.get("paths", {}).items()):
    methods = ", ".join(method.upper() for method in operations if method.lower() in allowed)
    print("{:^30} {}".format(methods, path))
