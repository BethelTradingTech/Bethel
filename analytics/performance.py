"""
Bethel Trading Technologies
Performance Analytics Engine
"""



class PerformanceAnalytics:


    def __init__(self, history):

        self.history = history



    def calculate(self):

        trades = self.history.get("history", [])


        if not trades:

            return {

                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0,
                "total_profit": 0,
                "profit_factor": 0

            }



        total_trades = len(trades)


        winning = [
            t for t in trades
            if t.get("profit", 0) > 0
        ]


        losing = [
            t for t in trades
            if t.get("profit", 0) < 0
        ]



        total_profit = sum(
            t.get("profit",0)
            for t in trades
        )


        gross_profit = sum(
            t.get("profit",0)
            for t in winning
        )


        gross_loss = abs(
            sum(
                t.get("profit",0)
                for t in losing
            )
        )



        profit_factor = (

            gross_profit / gross_loss

            if gross_loss > 0

            else 0

        )



        win_rate = (

            len(winning) / total_trades * 100

            if total_trades > 0

            else 0

        )



        return {


            "total_trades": total_trades,


            "winning_trades": len(winning),


            "losing_trades": len(losing),


            "win_rate": round(
                win_rate,
                2
            ),


            "total_profit": round(
                total_profit,
                2
            ),


            "profit_factor": round(
                profit_factor,
                2
            )


        }