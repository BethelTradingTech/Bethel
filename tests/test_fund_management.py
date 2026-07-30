from decimal import Decimal
import os
import unittest
from unittest.mock import patch

from api.fund_management.accounting import (
    calculate_nav,
    calculate_profit_share,
    calculate_subscription_units,
)
from api.fund_management.config import assert_safe_configuration


class FundAccountingTests(unittest.TestCase):
    def test_nav_uses_net_assets_and_decimal_precision(self):
        net_assets, nav = calculate_nav("125000", "5000", "100000")
        self.assertEqual(net_assets, Decimal("120000.00000000"))
        self.assertEqual(nav, Decimal("1.20000000"))

    def test_initial_nav_is_one_when_no_units_exist(self):
        net_assets, nav = calculate_nav("0", "0", "0")
        self.assertEqual(net_assets, Decimal("0E-8"))
        self.assertEqual(nav, Decimal("1"))

    def test_subscription_units_are_issued_at_current_nav(self):
        issued = calculate_subscription_units("25000", "1.25")
        self.assertEqual(issued, Decimal("20000.0000000000"))

    def test_profit_share_applies_only_above_high_water_mark(self):
        result = calculate_profit_share(
            account_units="10000",
            closing_nav_per_unit="1.30",
            high_water_mark_nav="1.10",
            fee_rate="0.20",
        )
        self.assertEqual(result, {
            "gross_eligible_profit": Decimal("2000.00000000"),
            "performance_fee": Decimal("400.00000000"),
            "investor_profit": Decimal("1600.00000000"),
        })

    def test_no_fee_when_nav_is_below_high_water_mark(self):
        result = calculate_profit_share(
            account_units="10000",
            closing_nav_per_unit="0.95",
            high_water_mark_nav="1.10",
            fee_rate="0.20",
        )
        self.assertEqual(result["gross_eligible_profit"], Decimal("0E-8"))
        self.assertEqual(result["performance_fee"], Decimal("0E-8"))
        self.assertEqual(result["investor_profit"], Decimal("0E-8"))

    def test_invalid_live_configuration_is_rejected(self):
        environment = {
            **os.environ,
            "FUND_PLATFORM_ENABLED": "true",
            "FUND_LIVE_TRADING": "true",
        }
        with patch.dict(os.environ, environment, clear=True):
            with self.assertRaisesRegex(
                RuntimeError,
                "Live pooled-fund operations are locked",
            ):
                assert_safe_configuration()

    def test_safe_sandbox_configuration_is_allowed(self):
        environment = {
            **os.environ,
            "FUND_PLATFORM_ENABLED": "true",
            "FUND_SIMULATED_EXECUTION": "true",
            "FUND_LIVE_DEPOSITS": "false",
            "FUND_LIVE_TRADING": "false",
            "FUND_LIVE_WITHDRAWALS": "false",
        }
        with patch.dict(os.environ, environment, clear=True):
            controls = assert_safe_configuration()
        self.assertTrue(controls["platform_enabled"])
        self.assertTrue(controls["simulated_execution"])


if __name__ == "__main__":
    unittest.main()
