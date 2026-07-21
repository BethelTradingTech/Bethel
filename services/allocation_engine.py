"""
Bethel Trading Technologies
Allocation Engine

Purpose:
Calculate subscriber trade allocation
from master account trades.

This module:
- Reads OPEN master trades
- Reads ACTIVE subscribers
- Calculates subscriber volume
- Creates allocation instructions

This module does NOT execute trades.
"""


import sys
import os


# ======================================
# PROJECT ROOT
# ======================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)



# ======================================
# DATABASE
# ======================================

from api.database import SessionLocal


# ======================================
# MODELS
# ======================================

from api.copytrading.models import (
    MasterTrade,
    CopySubscriber
)





class AllocationEngine:



    def __init__(self):

        pass





    # ======================================
    # CALCULATE SUBSCRIBER VOLUME
    # ======================================

    def calculate_volume(
        self,
        master_volume,
        allocation_percent,
        risk_multiplier
    ):

        """
        Calculate subscriber lot size.

        Formula:

        Master Volume
        x Allocation %
        x Risk Multiplier
        """

        volume = (

            master_volume

            *

            (allocation_percent / 100)

            *

            risk_multiplier

        )


        return round(
            volume,
            2
        )





    # ======================================
    # GENERATE ALLOCATIONS
    # ======================================

    def generate_allocations(self):


        database = SessionLocal()


        try:


            allocations = []



            # ------------------------------
            # GET OPEN MASTER TRADES
            # ------------------------------

            master_trades = (

                database.query(
                    MasterTrade
                )

                .filter(
                    MasterTrade.status == "OPEN"
                )

                .all()

            )



            # ------------------------------
            # GET ACTIVE SUBSCRIBERS
            # ------------------------------

            subscribers = (

                database.query(
                    CopySubscriber
                )

                .filter(
                    CopySubscriber.status == "ACTIVE"
                )

                .all()

            )




            # ------------------------------
            # BUILD ALLOCATIONS
            # ------------------------------

            for trade in master_trades:



                for subscriber in subscribers:



                    volume = self.calculate_volume(

                        trade.volume,

                        subscriber.allocation_percent,

                        subscriber.risk_multiplier

                    )



                    allocation = {


                        "subscriber_id":

                            subscriber.id,



                        "subscriber_account":

                            subscriber.mt5_account,



                        "master_ticket":

                            trade.ticket,



                        "symbol":

                            trade.symbol,



                        "direction":

                            trade.direction,



                        "volume":

                            volume,



                        "entry_price":

                            trade.entry_price,



                        "stop_loss":

                            trade.stop_loss,



                        "take_profit":

                            trade.take_profit

                    }



                    allocations.append(
                        allocation
                    )



            return allocations



        finally:


            database.close()





    # ======================================
    # TEST / CLEANUP
    # ======================================

    def close(self):

        pass







# ======================================
# TEST RUN
# ======================================

if __name__ == "__main__":



    engine = AllocationEngine()



    results = engine.generate_allocations()



    print(
        "Generated Allocations:",
        len(results)
    )



    for item in results:


        print(item)