from decimal import Decimal, ROUND_HALF_UP


ZERO = Decimal("0")
ONE = Decimal("1")
MONEY_QUANTUM = Decimal("0.00000001")
UNIT_QUANTUM = Decimal("0.0000000001")


def decimal_value(value) -> Decimal:
    return Decimal(str(value))


def money(value) -> Decimal:
    return decimal_value(value).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


def units(value) -> Decimal:
    return decimal_value(value).quantize(UNIT_QUANTUM, rounding=ROUND_HALF_UP)


def calculate_nav(gross_assets, liabilities, total_units) -> tuple[Decimal, Decimal]:
    gross = money(gross_assets)
    debts = money(liabilities)
    outstanding = units(total_units)
    if gross < ZERO or debts < ZERO:
        raise ValueError("Assets and liabilities cannot be negative")
    net_assets = money(gross - debts)
    if net_assets < ZERO:
        raise ValueError("Liabilities cannot exceed gross assets")
    nav_per_unit = ONE if outstanding == ZERO else money(net_assets / outstanding)
    return net_assets, nav_per_unit


def calculate_subscription_units(amount, nav_per_unit) -> Decimal:
    contribution = money(amount)
    nav = money(nav_per_unit)
    if contribution <= ZERO:
        raise ValueError("Subscription amount must be positive")
    if nav <= ZERO:
        raise ValueError("NAV per unit must be positive")
    return units(contribution / nav)


def calculate_profit_share(
    *,
    account_units,
    closing_nav_per_unit,
    high_water_mark_nav,
    fee_rate,
) -> dict:
    owned_units = units(account_units)
    closing_nav = money(closing_nav_per_unit)
    high_water_mark = money(high_water_mark_nav)
    rate = decimal_value(fee_rate)
    if owned_units < ZERO:
        raise ValueError("Account units cannot be negative")
    if closing_nav < ZERO or high_water_mark < ZERO:
        raise ValueError("NAV values cannot be negative")
    if rate < ZERO or rate > ONE:
        raise ValueError("Performance fee rate must be between 0 and 1")

    gain_per_unit = max(ZERO, closing_nav - high_water_mark)
    gross_profit = money(owned_units * gain_per_unit)
    performance_fee = money(gross_profit * rate)
    investor_profit = money(gross_profit - performance_fee)
    return {
        "gross_eligible_profit": gross_profit,
        "performance_fee": performance_fee,
        "investor_profit": investor_profit,
    }
