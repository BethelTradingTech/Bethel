"""
Bethel Trading Technologies
Monthly Performance Engine
"""


from collections import defaultdict

from api.services.daily_performance import DailyPerformanceEngine



class MonthlyPerformanceEngine:


    def __init__(self):

        self.daily_engine = DailyPerformanceEngine()



    # =====================================
    # MONTHLY RETURNS
    # =====================================

    def monthly_returns(self):


        curve = self.daily_engine.equity_history()


        if not curve:

            return []



        monthly = defaultdict(list)



        for item in curve:


            month = item["date"][:7]


            monthly[month].append(

                item["equity"]

            )



        results = []



        for month, values in sorted(monthly.items()):


            start = values[0]

            end = values[-1]



            if start == 0:

                continue



            performance = (

                (end - start)

                /

                start

            ) * 100



            results.append({

                "month": month,

                "return_percent":

                round(performance,2)

            })



        return results



    # =====================================
    # REPORT
    # =====================================

    def report(self):


        return {

            "status":

            "success",


            "monthly_performance":

            self.monthly_returns()

        }



def get_monthly_performance():


    engine = MonthlyPerformanceEngine()


    try:

        return engine.report()


    finally:

        engine.daily_engine.db.close()