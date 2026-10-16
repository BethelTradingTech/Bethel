# Bethel social live setup

Broadcasting is suspended. Keep the Render broadcast service suspended and the
Broadcast Engine disabled until the owner explicitly requests resumption.
This branch prepares five-platform support; it does not activate any destination.

## Private worker settings

Set each full ingest URL (server URL plus stream key, as provided by the platform)
in the **bethel-broadcast** service environment. Never place keys in the repository,
frontend, screenshots, or chat. A TikTok OAuth connection is separate from LIVE
ingest access.

| Destination | Worker environment variable | Layout |
| --- | --- | --- |
| YouTube | `YOUTUBE_RTMPS_URL` | Landscape |
| Facebook | `FACEBOOK_RTMPS_URL` | Landscape |
| Instagram | `INSTAGRAM_RTMPS_URL` | Vertical |
| TikTok | `TIKTOK_RTMPS_URL` | Vertical |
| X | `X_RTMPS_URL` | Landscape |

The Super Admin readiness endpoint reports only whether each setting is present.
It does not expose its value or verify account eligibility, key validity, or delivery.
While the worker is suspended, readiness cannot be queried.

## Remaining account checks

1. Identify the correct Bethel profile/channel on all five platforms.
2. Check each account's live dashboard for external encoder access and its current
   ingest instructions. Record blockers without assuming that OAuth or follower
   counts grant encoder access.
3. Enter the current ingest credentials privately. Session-specific keys may need
   replacement before each broadcast.
4. After authorization to resume, deploy the worker and API/admin changes, select
   an owner/master source, and use available private or preview modes to inspect
   video, audio, privacy, and delivery on each platform.
5. Confirm receipt in each platform's dashboard. The existing HLS `STREAMING`
   state alone does not prove social delivery. Public broadcasting requires a
   separate launch decision.

## Validation

`python -m pytest tests/test_broadcast_destinations.py -q`

Tests cover migration of an existing control row with X disabled, opt-in X
landscape routing, readiness authentication, and credential redaction.
