# Public Verified Track Record Contract

Bethel's public performance presentation is intentionally stable.

## Presentation
- Keep the calendar return matrix in this order: `Year | Jan | Feb | Mar | Apr | May | Jun | Jul | Aug | Sep | Oct | Nov | Dec | Year`.
- Monthly cells display the active master's actual reconciled return for that month.
- Missing periods display an em dash rather than invented data.
- Positive and negative periods remain visually distinguishable.
- The final Year column is the compounded result of the available monthly returns.

## Dynamic data source
- No MT5 account number or historical return is entered into the public renderer.
- The backend dynamically resolves the active Bethel owner/master account from signed runtime snapshots.
- Subscriber terminals cannot become the company master merely because they submitted a newer snapshot.
- Public summary, history, risk statistics and monthly returns are scoped to the dynamically resolved active master.
- The public renderer refreshes automatically and rejects a refresh if the master changes while summary/history are being loaded.

## Change control
The layout and source-of-truth behavior are protected by `scripts/check_public_track_record_contract.py` and the `Public Track Record Contract` GitHub Actions workflow. A future code change that removes these guarantees should fail CI and must be treated as an intentional product-policy change rather than a routine frontend redesign.
