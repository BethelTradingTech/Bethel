"""
Bethel Trading Technologies
Advanced Performance Analytics Engine
"""


class AdvancedAnalytics:


    def __init__(self, history):

        self.history = history or []



    def calculate(self):


        profits = []


        for trade in self.history:


            profit = trade.get(
                "profit",
                0
            )


            try:

                profit = float(profit)

            except:

                profit = 0



            profits.append(profit)





        if not profits:


            return {

                "roi":0,

                "average_win":0,

                "average_loss":0,

                "largest_win":0,

                "largest_loss":0,

                "profit_days":0,

                "loss_days":0,

                "recovery_factor":0,

                "sharpe_ratio":0

            }




        wins = [

            p for p in profits

            if p > 0

        ]



        losses = [

            p for p in profits

            if p < 0

        ]





        total_profit = sum(profits)



        average_win = (

            sum(wins) / len(wins)

            if wins

            else 0

        )



        average_loss = (

            sum(losses) / len(losses)

            if losses

            else 0

        )





        largest_win = max(

            profits

        )



        largest_loss = min(

            profits

        )





        profit_days = len(wins)


        loss_days = len(losses)





        recovery_factor = (

            total_profit /

            abs(largest_loss)

            if largest_loss < 0

            else 0

        )





        sharpe_ratio = (

            total_profit /

            len(profits)

            if profits

            else 0

        )





        return {


            "roi":

            round(total_profit / 100000 * 100,2),



            "average_win":

            round(average_win,2),



            "average_loss":

            round(average_loss,2),



            "largest_win":

            round(largest_win,2),



            "largest_loss":

            round(largest_loss,2),



            "profit_days":

            profit_days,



            "loss_days":

            loss_days,



            "recovery_factor":

            round(recovery_factor,2),



            "sharpe_ratio":

            round(sharpe_ratio,2)


        }