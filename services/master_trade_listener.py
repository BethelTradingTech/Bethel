"""
Bethel Trading Technologies

Master Trade Listener

Purpose:
    Reads master MT5 account positions.
    Stores them in master_trades table.
    Automatically creates subscriber copy orders.

Flow:

MASTER MT5
    |
    v
MasterTradeListener
    |
    v
master_trades
    |
    v
CopyTradingService
    |
    v
copy_orders
"""


import sys
import os
import time

from datetime import datetime, timezone


# ======================================================
# PROJECT ROOT
# ======================================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

sys.path.append(PROJECT_ROOT)



# ======================================================
# INTERNAL IMPORTS
# ======================================================

from api.database import SessionLocal

from api.copytrading import models

from api.copytrading.models import MasterTrade

from api.copytrading.service import CopyTradingService

from mt5_connector.positions import MT5Positions



class MasterTradeListener:


    def __init__(self):

        self.positions = MT5Positions()



    # ==================================================
    # SAVE / UPDATE MASTER POSITION
    # ==================================================

    def save_position(self, position):


        db = SessionLocal()


        try:

            ticket = position["ticket"]



            existing = (
                db.query(MasterTrade)
                .filter(
                    MasterTrade.ticket == ticket
                )
                .first()
            )



            direction = (

                "BUY"

                if position["type"] == 0

                else

                "SELL"

            )



            # ==========================================
            # UPDATE EXISTING TRADE
            # ==========================================

            if existing:


                existing.current_price = (
                    position["price_current"]
                )

                existing.profit = (
                    position["profit"]
                )

                existing.stop_loss = (
                    position["sl"]
                )

                existing.take_profit = (
                    position["tp"]
                )

                existing.last_seen = (
                    datetime.now(timezone.utc)
                )

                existing.status = "OPEN"



                db.commit()



                print(
                    "UPDATED MASTER TRADE:",
                    ticket
                )



                return



            # ==========================================
            # CREATE NEW MASTER TRADE
            # ==========================================


            trade = MasterTrade(


                ticket=ticket,


                symbol=position["symbol"],


                direction=direction,


                volume=position["volume"],


                entry_price=position["price_open"],


                stop_loss=position["sl"],


                take_profit=position["tp"],


                current_price=position["price_current"],


                profit=position["profit"],


                status="OPEN",


                opened_at=datetime.now(timezone.utc),


                last_seen=datetime.now(timezone.utc)

            )



            db.add(trade)

            db.commit()

            db.refresh(trade)



            print(
                "NEW MASTER TRADE:",
                ticket
            )



            # ==========================================
            # CREATE COPY ORDERS
            # ==========================================


            subscribers = (

                db.query(
                    models.CopySubscriber
                )

                .filter(
                    models.CopySubscriber.status
                    ==
                    "ACTIVE"
                )

                .all()

            )



            created_orders = []



            for subscriber in subscribers:


                copy_order = (

                    CopyTradingService
                    .create_copy_order(

                        db,

                        subscriber,

                        trade

                    )

                )


                created_orders.append(
                    copy_order.id
                )



            print(
                "COPY ORDERS CREATED:",
                created_orders
            )



        except Exception as error:


            db.rollback()


            print(
                "MASTER LISTENER ERROR:",
                error
            )



        finally:


            db.close()



    # ==================================================
    # SCAN MT5 POSITIONS
    # ==================================================

    def scan(self):


        data = (
            self.positions.get_positions()
        )



        if data["status"] != "success":


            print(
                "MT5 POSITION ERROR:",
                data
            )


            return



        for position in data["positions"]:


            self.save_position(
                position
            )



    # ==================================================
    # CONTINUOUS LISTENER
    # ==================================================

    def run(self):


        print(
            "Master Trade Listener Started"
        )



        while True:


            try:


                self.scan()



            except Exception as error:


                print(
                    "LISTENER LOOP ERROR:",
                    error
                )



            time.sleep(5)





# ======================================================
# START SERVICE
# ======================================================

if __name__ == "__main__":


    listener = MasterTradeListener()

    listener.run()