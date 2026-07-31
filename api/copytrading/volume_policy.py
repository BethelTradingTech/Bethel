"""Copy-volume policy for standard and cent subscriber accounts."""

from decimal import Decimal, ROUND_HALF_UP


CENT_CAPITAL_LIMIT_USD = Decimal("1000")
MIN_COPY_VOLUME = Decimal("0.01")


def cent_capital_multiplier(starting_capital_usd: float) -> float:
    capital = Decimal(str(starting_capital_usd))
    if capital <= 0 or capital >= CENT_CAPITAL_LIMIT_USD:
        raise ValueError("Cent-account starting capital must be above 0 and below 1000 USD")
    return float(min(Decimal("1"), capital / CENT_CAPITAL_LIMIT_USD))


def calculate_copy_volume(
    master_volume: float,
    *,
    account_type: str = "STANDARD",
    starting_capital_usd: float | None = None,
) -> float:
    master = Decimal(str(master_volume))
    if master <= 0:
        raise ValueError("Master volume must be positive")

    if str(account_type).upper() != "CENT":
        volume = master
    else:
        if starting_capital_usd is None:
            raise ValueError("Cent account requires starting capital")
        volume = master * Decimal(str(cent_capital_multiplier(starting_capital_usd)))
        volume = max(MIN_COPY_VOLUME, volume)

    return float(volume.quantize(MIN_COPY_VOLUME, rounding=ROUND_HALF_UP))


def calculate_subscriber_volume(db, master_volume: float, subscriber_id: int) -> float:
    from api.broker_accounts.models import BrokerAccount

    account = db.query(BrokerAccount).filter(
        BrokerAccount.subscriber_id == subscriber_id
    ).first()
    if account is None:
        return calculate_copy_volume(master_volume)

    return calculate_copy_volume(
        master_volume,
        account_type=account.account_type,
        starting_capital_usd=account.starting_capital_usd,
    )
