import os
import sys
import time

from datetime import datetime


# ==========================================
# PROJECT PATH
# ==========================================

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)


if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)



# ==========================================
# IMPORT SERVICES
# ==========================================

from services.master_trade_listener import MasterTradeListener

from services.copy_engine import CopyEngine

from services.copy_execution_manager import CopyExecutionManager




class CopyTradingService:



    def __init__(self):


        self.listener = MasterTradeListener()

        self.copy_engine = CopyEngine()

        self.execution_manager = CopyExecutionManager()

        self.running = False





    # ==========================================
    # RUN ONE CYCLE
    # ==========================================


    def run_once(self):


        print()

        print("=" * 50)

        print(
            datetime.now(),
            "COPY TRADING CYCLE"
        )

        print("=" * 50)



        # 1. Update master trades

        print(
            "Updating master trades..."
        )


        self.listener.scan()



        # 2. Generate copy orders

        print(
            "Generating copy orders..."
        )


        self.copy_engine.run()



        # 3. Execute pending copies

        print(
            "Processing executions..."
        )


        self.execution_manager.run()



        print(
            "Cycle completed"
        )





    # ==========================================
    # START SERVICE
    # ==========================================


    def start(

        self,

        interval_seconds=10

    ):


        self.running = True



        print(
            "Bethel Trading Technologies Copy Trading Service Started"
        )



        while self.running:



            try:


                self.run_once()



            except Exception as error:


                print(

                    "Copy Service Error:",

                    error

                )



            time.sleep(

                interval_seconds

            )





    # ==========================================
    # STOP
    # ==========================================


    def stop(self):


        self.running = False






# ==========================================
# START
# ==========================================


if __name__ == "__main__":


    service = CopyTradingService()


    service.start(
        interval_seconds=10
    )