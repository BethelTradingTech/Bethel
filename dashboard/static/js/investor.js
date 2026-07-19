const INVESTOR_ID = 1;

/*
Bethel Trading Technologies
Investor Dashboard Engine v6
Unified Investor + MT5 Analytics
*/


const API = "http://127.0.0.1:8000";


let equityChart = null;
let monthlyChart = null;
let tradeChart = null;



// ======================================
// API CONNECTION
// ======================================


async function getData(url){

    try{

        const response = await fetch(

            API +
            url +
            "?t=" +
            Date.now()

        );


        if(!response.ok){

            throw new Error(
                "API Error: " + url
            );

        }


        return await response.json();


    }

    catch(error){

        console.log(
            "API ERROR:",
            error
        );


        return null;

    }

}



// ======================================
// FORMATTERS
// ======================================


function money(value){

    if(
        value === null ||
        value === undefined ||
        isNaN(value)
    ){

        return "$0.00";

    }


    return "$" +

    Number(value).toLocaleString(

        undefined,

        {

            minimumFractionDigits:2,

            maximumFractionDigits:2

        }

    );

}



function percent(value){

    if(
        value === null ||
        value === undefined ||
        isNaN(value)
    ){

        return "--";

    }


    return Number(value).toFixed(2) + "%";

}




function number(value){

    if(
        value === null ||
        value === undefined ||
        isNaN(value)
    ){

        return "--";

    }


    return Number(value).toFixed(2);

}




function safe(id,value){

    const element =
        document.getElementById(id);


    if(element){

        element.innerHTML = value;

    }

}


/*
======================================
EQUITY HISTORY ENGINE
======================================
*/


async function loadEquity(){


    const data = await getData(

        "/performance/equity-history"

    );



    if(

        !data ||

        !data.history ||

        data.history.length === 0

    ){

        return;

    }



    const history =

        data.history.slice(-100);



    const latest =

        history[

            history.length - 1

        ];





    // ==================================
    // ACCOUNT OVERVIEW
    // ==================================



    safe(

        "balance",

        money(

            latest.balance

        )

    );



    safe(

        "equity",

        money(

            latest.equity

        )

    );



    safe(

        "profit",

        money(

            latest.profit

        )

    );



    safe(

        "drawdown",

        percent(

            latest.drawdown

        )

    );






    // ==================================
    // EQUITY CURVE CHART
    // ==================================



    const chart =

        document.getElementById(

            "equityChart"

        );



    if(!chart){

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


/*
======================================
TRADE PERFORMANCE ENGINE
======================================
*/


async function loadTrades(){


    const data = await getData(

        "/performance/trades"

    );



    if(!data){

        return;

    }




    const performance =

        data.performance || {};



    const risk =

        data.risk || {};






    // ==================================
    // TRADE STATISTICS
    // ==================================


    safe(

        "trades",

        performance.total_trades ?? "--"

    );



    safe(

        "winrate",

        percent(

            performance.win_rate

        )

    );



    safe(

        "profitfactor",

        number(

            performance.profit_factor

        )

    );






    // ==================================
    // RISK METRICS
    // ==================================


    safe(

        "sharpe",

        number(

            risk.sharpe_ratio

        )

    );



    safe(

        "sortino",

        number(

            risk.sortino_ratio

        )

    );



    safe(

        "maxdd",

        money(

            risk.max_drawdown

        )

    );







    // ==================================
    // TRADE DISTRIBUTION CHART
    // ==================================


    const chart =

        document.getElementById(

            "tradeChart"

        );



    if(!chart){

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


/*
======================================
INVESTOR ANALYTICS ENGINE
======================================
*/


async function loadInvestorAnalytics(){


    const analytics = await getData(

        "/performance/analytics"

    );



    if(!analytics){

        return;

    }






    // ==================================
    // SYSTEM STATUS
    // ==================================


    safe(

        "status",

        analytics.status ?? "ONLINE"

    );







    // ==================================
    // CAPITAL INFORMATION
    // ==================================


    safe(

        "startingCapital",

        money(

            analytics.starting_capital

        )

    );



    safe(

        "currentEquity",

        money(

            analytics.current_equity

        )

    );







    // ==================================
    // PERFORMANCE RETURNS
    // ==================================


    safe(

        "return",

        percent(

            analytics.total_return_percent

        )

    );



    safe(

        "growth",

        percent(

            analytics.total_return_percent

        )

    );







    // ==================================
    // TRADING PERFORMANCE
    // ==================================


    safe(

        "trades",

        analytics.total_trades ?? "--"

    );



    safe(

        "winrate",

        percent(

            analytics.win_rate

        )

    );



    safe(

        "profitfactor",

        number(

            analytics.profit_factor

        )

    );







    // ==================================
    // INVESTOR QUALITY SCORE
    // ==================================


    safe(

        "grade",

        analytics.performance_grade ?? "--"

    );



    safe(

        "risk",

        analytics.risk_level ?? "--"

    );



    safe(

        "consistency",

        number(

            analytics.consistency_score

        )

    );



    safe(

        "recovery",

        number(

            analytics.recovery_factor

        )

    );







    // ==================================
    // RISK ANALYTICS TABLE
    // ==================================


    safe(

        "sharpe",

        number(

            analytics.sharpe_ratio

        )

    );



    safe(

        "sortino",

        number(

            analytics.sortino_ratio

        )

    );



    safe(

        "maxdd",

        money(

            analytics.maximum_drawdown_amount

        )

    );



    safe(

        "volatility",

        percent(

            analytics.volatility

        )

    );



    safe(

        "snapshots",

        analytics.snapshots_analyzed ?? "--"

    );



}


/*
======================================
MONTHLY PERFORMANCE ENGINE
======================================
*/


async function loadMonthly(){


    const data = await getData(

        "/performance/monthly"

    );



    if(!data){

        return;

    }



    const monthly =

        data.monthly_performance;



    if(

        !monthly ||

        monthly.length === 0

    ){

        return;

    }




    const chart =

        document.getElementById(

            "monthlyChart"

        );



    if(!chart){

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







/*
======================================
INVESTOR MASTER DASHBOARD
======================================
*/


async function loadInvestorDashboard(){


    const data = await getData(

        "/investor/api/dashboard/" + INVESTOR_ID

    );


    if(!data){

        return;

    }



    if(data.investor){


        safe(
            "investorName",
            data.investor.name ?? "--"
        );


        safe(
            "investorEmail",
            data.investor.email ?? "--"
        );

    }




    if(data.portfolio){


        safe(
            "portfolioName",
            data.portfolio.name ?? "--"
        );


        safe(
            "portfolioCapital",
            money(data.portfolio.capital)
        );


        safe(
            "portfolioValue",
            money(data.portfolio.current_value)
        );


    }





    if(data.mt5){


        safe(
            "mt5Login",
            data.mt5.login ?? "--"
        );


        safe(
            "mt5Server",
            data.mt5.server ?? "--"
        );


        safe(
            "mt5Currency",
            data.mt5.currency ?? "--"
        );


    }


}



/*
======================================
MT5 ACCOUNT VERIFICATION
======================================
*/


async function loadMT5(){


    const data = await getData(

        "/investor/api/mt5"

    );



    if(!data){

        return;

    }



    safe(

        "mt5Status",

        data.status ?? "--"

    );



    safe(

        "mt5Login",

        data.login ?? "--"

    );



    safe(

        "mt5Server",

        data.server ?? "--"

    );



    safe(

        "mt5Currency",

        data.currency ?? "--"

    );



    safe(

        "mt5Leverage",

        data.leverage ?? "--"

    );



}







/*
======================================
LIVE POSITIONS TABLE
======================================
*/


async function loadPositions(){


    const data = await getData(

        "/mt5/positions"

    );



    const table =

        document.getElementById(

            "positionsTable"

        );



    if(

        !table ||

        !data ||

        !data.positions

    ){

        return;

    }




    table.innerHTML = "";




    data.positions.forEach(

        position => {


            table.innerHTML += `


<tr>

<td>
${position.symbol}
</td>


<td>
${position.type}
</td>


<td>
${position.volume}
</td>


<td>
${money(position.profit)}
</td>


</tr>


`;

        }

    );


}







/*
======================================
TRADE HISTORY TABLE
======================================
*/


async function loadHistory(){


    const data = await getData(

        "/mt5/history"

    );



    const table =

        document.getElementById(

            "historyTable"

        );



    if(

        !table ||

        !data ||

        !data.history

    ){

        return;

    }




    table.innerHTML = "";




    data.history.forEach(

        trade => {


            table.innerHTML += `


<tr>


<td>
${trade.symbol}
</td>


<td>
${trade.type}
</td>


<td>
${trade.volume}
</td>


<td>
${money(trade.profit)}
</td>


<td>
${trade.time}
</td>


</tr>


`;

        }

    );


}







/*
======================================
DASHBOARD LOADER
======================================
*/


async function loadDashboard(){


    await loadInvestorDashboard();


    await loadEquity();


    await loadTrades();


    await loadMonthly();


    await loadInvestorAnalytics();


    await loadMT5();


    await loadPositions();


    await loadHistory();


}







/*
======================================
START APPLICATION
======================================
*/


window.addEventListener(

    "load",

    function(){


        loadDashboard();



        // Refresh every 30 seconds


        setInterval(

            loadDashboard,

            30000

        );


    }

);