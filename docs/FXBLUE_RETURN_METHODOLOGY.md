# FX Blue-style normalized return research

Status: research only. This document does not authorize changing the production `/performance/analytics` endpoint.

## Confirmed facts

FX Blue states that deposits and withdrawals split performance into subperiods and that the subperiod returns are geometrically compounded. A deposit or withdrawal is not treated as trading performance.

Official reference:
- https://api.fxblue.com/faq/multiple-deposits

Myfxbook defines its headline Daily and Monthly figures as the constant compound rate required over the account lifetime to reproduce the account gain. These are normalized lifetime-equivalent rates, not necessarily the realized return in the latest day or calendar month.

Official reference:
- https://www.myfxbook.com/help/knowledge-base/daily-and-monthly/

Darwinex uses equity at the start and end of the requested timeframe, including realized P/L, unrealized P/L, and cash-flow adjustment. This is an actual timeframe return and is a separate concept from FX Blue/Myfxbook headline normalized returns.

Official reference:
- https://help.darwinex.com/return

## Bethel account evidence

FX Blue screenshot for account `37371080` showed:

- Banked return: `51.92%`
- History: `27` calendar days
- Trading days from 2026-07-10 through 2026-08-05 inclusive: `19`
- Per day: `2.23%`
- Per week: `11.63%`
- Per month: `58.76%`

The figures reproduce exactly, before display rounding, when using the banked compound return and 19 trading days:

```text
daily = (1 + 0.5192)^(1 / 19) - 1
       = 0.0222536777 = 2.22536777%

weekly = (1 + daily)^5 - 1
        = 11.63320880%

monthly = (1 + daily)^21 - 1
         = 58.75679220%
```

Rounded to two decimal places:

- Daily: `2.23%`
- Weekly: `11.63%`
- Monthly: `58.76%`

## Interpretation

The screenshot strongly supports this hypothesis for FX Blue headline returns:

1. Compute a cash-flow-neutral compounded banked return.
2. Count elapsed trading weekdays in the history.
3. Convert the banked return to an equivalent daily compound rate.
4. Compound the daily rate over 5 trading days for the weekly equivalent.
5. Compound the daily rate over 21 trading days for the monthly equivalent.

This is distinct from:

- rolling 1-day, 7-day, or 30-day realized return;
- current calendar-week or calendar-month return;
- Darwinex-style equity return for a selected timeframe.

## Required naming in Bethel

To avoid misleading investors, Bethel should keep these concepts separate:

### Normalized headline returns

- `average_daily_return_percent`
- `average_weekly_return_percent`
- `average_monthly_return_percent`

Method label:

```text
cash_flow_neutral_banked_return_geometric_equivalent
```

### Actual timeframe returns

- `rolling_1d_return_percent`
- `rolling_7d_return_percent`
- `rolling_30d_return_percent`
- `calendar_month_return_percent`

Method label should identify whether the source is balance or equity.

## Safety gates

The normalized calculation must return unavailable when:

- trading-day count is zero or negative;
- banked return is `-100%` or worse;
- cash-flow-adjusted banked return is unavailable;
- account identity is missing or ambiguous.

No normalized return code should replace production fields until the live account output is compared with FX Blue and approved explicitly.
