"""
Bethel Trading Technologies
Professional Equity Curve Analytics Engine
"""


class EquityCurve:


    def __init__(
        self,
        history,
        starting_balance=100000
    ):

        self.history = history

        self.starting_balance = starting_balance



    def calculate(self):


        trades = self.history.get(
            "history",
            []
        )


        if not trades:

            return {

                "status": "empty",

                "equity_curve": [],

                "drawdown": [],

                "metrics": {}

            }



        equity = self.starting_balance


        peak_equity = equity


        max_drawdown = 0


        curve = []


        drawdown_history = []



        total_profit = 0



        for trade in trades:


            profit = float(
                trade.get(
                    "profit",
                    0
                )
            )


            equity += profit


            total_profit += profit



            if equity > peak_equity:

                peak_equity = equity



            drawdown = (

                (peak_equity - equity)

                /

                peak_equity

            ) * 100



            if drawdown > max_drawdown:

                max_drawdown = drawdown




            curve.append({

                "time":
                    trade.get(
                        "time"
                    ),


                "equity":
                    round(
                        equity,
                        2
                    )

            })




            drawdown_history.append({

                "time":
                    trade.get(
                        "time"
                    ),


                "drawdown":
                    round(
                        drawdown,
                        2
                    )

            })






        total_return = (

            (

                equity

                -

                self.starting_balance

            )

            /

            self.starting_balance

        ) * 100





        recovery_factor = 0


        if max_drawdown > 0:

            recovery_factor = (

                total_return

                /

                max_drawdown

            )





        return {


            "status":
                "success",



            "starting_balance":
                self.starting_balance,



            "current_equity":
                round(
                    equity,
                    2
                ),



            "equity_curve":
                curve,



            "drawdown":
                drawdown_history,



            "metrics": {


                "total_profit":
                    round(
                        total_profit,
                        2
                    ),



                "total_return_percent":
                    round(
                        total_return,
                        2
                    ),



                "max_drawdown_percent":
                    round(
                        max_drawdown,
                        2
                    ),



                "recovery_factor":
                    round(
                        recovery_factor,
                        2
                    )


            }


        }