"""
Bethel Trading Technologies
Main Platform Controller
"""

from config import settings
from core.logger import get_logger
from database.database import database_status


logger = get_logger("BETHEL_SYSTEM")


def start_platform():

    print("=" * 40)
    print("BETHEL TRADING TECHNOLOGIES")
    print("QUANT PLATFORM")
    print("=" * 40)

    print()

    print(f"Version: {settings.VERSION}")
    print(f"Environment: {settings.ENVIRONMENT}")

    print()

    print("Modules:")

    print("✓ Configuration Loaded")

    logger.info(
        "Bethel Trading Technologies Started"
    )

    print("✓ Logging Online")

    print(
        f"✓ {database_status()}"
    )

    print()

    print("System Status: READY")

    print("=" * 40)



if __name__ == "__main__":

    start_platform()