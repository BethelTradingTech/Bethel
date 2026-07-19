"""
Bethel Trading Technologies
Equity Snapshot Scheduler

Automatically records MT5 account performance.
"""


import time

from datetime import datetime


from services.equity_collector import EquityCollector





class EquityScheduler:



    def __init__(self):

        self.collector = EquityCollector()

        self.running = False



    # ==========================
    # RUN ONCE
    # ==========================

    def run_once(self):


        print(
            f"[{datetime.now()}] Collecting equity snapshot..."
        )


        result = self.collector.collect()


        print(result)



    # ==========================
    # START SCHEDULER
    # ==========================

    def start(

        self,

        interval_seconds=3600

    ):


        self.running = True


        print(

            "Bethel Trading Technologies Equity Scheduler Started"

        )


        while self.running:


            try:


                self.run_once()



            except Exception as e:


                print(

                    "Scheduler Error:",

                    e

                )



            time.sleep(

                interval_seconds

            )



    # ==========================
    # STOP
    # ==========================

    def stop(self):


        self.running = False



# ==========================
# START SERVICE
# ==========================


if __name__ == "__main__":


    scheduler = EquityScheduler()



    # Test interval:
    # Change to 3600 for hourly collection

    scheduler.start(

        interval_seconds=3600

    )