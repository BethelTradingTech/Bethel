/*
Bethel Trading Technologies
Investor Dashboard Charts Engine
Phase 7 Frontend Architecture
*/


let equityChart = null;

let monthlyChart = null;

let tradeChart = null;




// ======================================
// EQUITY CHART
// ======================================


function drawEquityChart(history){


    const chart =

        document.getElementById(
            "equityChart"
        );



    if(!chart || !history){

        return;

    }




    if(equityChart){

        equityChart.destroy();

    }




    equityChart = new Chart(

        chart,

        {

            type:"line",


            data:{


                labels:

                    history.map(

                        item =>

                        item.timestamp

                    ),



                datasets:[{


                    label:

                    "Equity Growth Curve",



                    data:

                        history.map(

                            item =>

                            item.equity

                        )


                }]


            },


            options:{


                responsive:true,


                maintainAspectRatio:false


            }


        }


    );


}







// ======================================
// MONTHLY PERFORMANCE CHART
// ======================================


function drawMonthlyChart(monthly){


    const chart =

        document.getElementById(
            "monthlyChart"
        );



    if(!chart || !monthly){

        return;

    }




    if(monthlyChart){

        monthlyChart.destroy();

    }




    monthlyChart = new Chart(

        chart,

        {


            type:"bar",



            data:{


                labels:

                    monthly.map(

                        item =>

                        item.month

                    ),



                datasets:[{


                    label:

                    "Monthly Return %",



                    data:

                        monthly.map(

                            item =>

                            item.return_percent

                        )


                }]


            },



            options:{


                responsive:true,


                maintainAspectRatio:false


            }



        }


    );


}







// ======================================
// TRADE DISTRIBUTION CHART
// ======================================


function drawTradeChart(performance){


    const chart =

        document.getElementById(
            "tradeChart"
        );



    if(!chart || !performance){

        return;

    }





    if(tradeChart){

        tradeChart.destroy();

    }






    tradeChart = new Chart(

        chart,

        {


            type:"doughnut",



            data:{


                labels:[


                    "Winning Trades",

                    "Losing Trades"


                ],




                datasets:[{


                    label:

                    "Trade Results",



                    data:[


                        performance.winning_trades ?? 0,


                        performance.losing_trades ?? 0


                    ]


                }]


            },



            options:{


                responsive:true,


                maintainAspectRatio:false


            }



        }


    );



}