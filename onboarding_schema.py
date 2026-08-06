import json
from main import app
schema = app.openapi()
targets = [
    "/onboarding/plans",
    "/onboarding/{subscriber_id}",
    "/onboarding/{subscriber_id}/subscription",
    "/onboarding/{subscriber_id}/kyc/submit",
    "/onboarding/{subscriber_id}/payment/confirm",
    "/onboarding/{subscriber_id}/broker/refresh",
    "/onboarding/{subscriber_id}/approval",
    "/broker-accounts/link",
    "/broker-accounts/subscriber/{subscriber_id}",
    "/copytrading/onboarding/connect-mt5/{subscriber_id}",
]
result = {"paths": {}, "schemas": schema.get("components", {}).get("schemas", {})}
for path in targets:
    if path in schema.get("paths", {}):
        result["paths"][path] = schema["paths"][path]
print(json.dumps(result, indent=2))
