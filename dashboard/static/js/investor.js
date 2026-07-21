/*
Bethel Trading Technologies

File:
investor.js

Phase 7:
Secure Investor Dashboard Frontend

Responsibilities:

- Investor profile
- Portfolio data
- Performance analytics
- Equity curve
- Trade analytics
- MT5 monitoring
- Live positions
- Trade history
- Copy trading dashboard

*/


// ======================================
// GLOBAL CONFIGURATION
// ======================================


const REFRESH_INTERVAL = 30000;




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


// ======================================
// INVESTOR PROFILE ENGINE
// ======================================


async function loadInvestorDashboard(){


    const investorId = getInvestorId();


    if(!investorId){

        console.error(
            "Investor ID missing from JWT"
        );

        return;

    }



    const data = await apiGet(

        "/investor/api/dashboard/" +

        investorId

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
            money(
                data.portfolio.capital
            )
        );


        safe(
            "portfolioValue",
            money(
                data.portfolio.current_value
            )
        );

    }


}



// ======================================
// EQUITY ENGINE
// ======================================


async function loadEquity(){


    const data = await apiGet(

        "/performance/equity-history"

    );



    if(

        !data ||

        !data.history ||

        data.history.length === 0

    ){

        return;

    }



    const history = data.history.slice(-100);



    const latest = history[

        history.length - 1

    ];



    safe(

        "balance",

        money(

            latest.balance

        )

    );



    safe(

        "currentEquity",

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



    if(typeof drawEquityChart === "function"){


        drawEquityChart(

            history

        );


    }


}





// ======================================
// ANALYTICS ENGINE
// ======================================


async function loadAnalytics(){


    const data = await apiGet(

        "/performance/analytics"

    );



    if(!data){

        return;

    }



    safe(

        "status",

        data.status ?? "ONLINE"

    );



    safe(

        "startingCapital",

        money(

            data.starting_capital

        )

    );



    safe(

        "currentEquity",

        money(

            data.current_equity

        )

    );



    safe(

        "return",

        percent(

            data.total_return_percent

        )

    );



    safe(

        "grade",

        data.performance_grade ?? "--"

    );



    safe(

        "risk",

        data.risk_level ?? "--"

    );



    safe(

        "consistency",

        number(

            data.consistency_score

        )

    );



    safe(

        "recovery",

        number(

            data.recovery_factor

        )

    );



    safe(

        "sharpe",

        number(

            data.sharpe_ratio

        )

    );



    safe(

        "sortino",

        number(

            data.sortino_ratio

        )

    );



    safe(

        "volatility",

        percent(

            data.volatility

        )

    );



    safe(

        "maxdd",

        money(

            data.maximum_drawdown_amount

        )

    );



    safe(

        "snapshots",

        data.snapshots_analyzed ?? "--"

    );


}



// ======================================
// TRADE PERFORMANCE ENGINE
// ======================================


async function loadTrades(){


    const data = await apiGet(

        "/performance/trades"

    );



    if(!data){

        return;

    }



    const performance =

        data.performance || data;



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



    if(typeof drawTradeChart === "function"){


        drawTradeChart(

            performance

        );


    }


}






// ======================================
// MONTHLY PERFORMANCE ENGINE
// ======================================


async function loadMonthly(){


    const data = await apiGet(

        "/performance/monthly"

    );



    if(!data){

        return;

    }



    if(data.monthly_performance){


        if(typeof drawMonthlyChart === "function"){


            drawMonthlyChart(

                data.monthly_performance

            );


        }

    }


}



// ======================================
// MT5 ACCOUNT ENGINE
// ======================================


async function loadMT5(){


    const data = await apiGet(

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






// ======================================
// LIVE POSITIONS ENGINE
// ======================================


async function loadPositions(){


    const data = await apiGet(

        "/mt5/positions"

    );



    const table = document.getElementById(

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
${position.symbol ?? "--"}
</td>

<td>
${position.type ?? "--"}
</td>

<td>
${position.volume ?? "--"}
</td>

<td>
${money(position.profit)}
</td>

</tr>

`;

        }

    );


}






// ======================================
// TRADE HISTORY ENGINE
// ======================================


async function loadHistory(){


    const data = await apiGet(

        "/mt5/history"

    );



    const table = document.getElementById(

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
${trade.symbol ?? "--"}
</td>

<td>
${trade.type ?? "--"}
</td>

<td>
${trade.volume ?? "--"}
</td>

<td>
${money(trade.profit)}
</td>

<td>
${trade.time ?? "--"}
</td>

</tr>

`;

        }

    );


}



// ======================================
// COPY TRADING DASHBOARD
// ======================================


async function loadCopyTradingDashboard(){


    const data = await apiGet(

        "/copytrading/dashboard"

    );



    if(!data){

        return;

    }



    safe(

        "copyMode",

        data.mode ?? "PAPER"

    );



    safe(

        "copySubscribers",

        data.subscribers?.total ?? 0

    );



    safe(

        "copyMasterTrades",

        data.trading?.master_trades ?? 0

    );



    safe(

        "copyOrders",

        data.trading?.copy_orders ?? 0

    );



    safe(

        "copyExecutedOrders",

        data.trading?.executed_orders ?? 0

    );



    safe(

        "copyExecutionLogs",

        data.execution_logs ?? 0

    );


}



// ======================================
// MASTER DASHBOARD LOADER
// ======================================


async function loadDashboard(){


    try{


        await Promise.all([


            loadInvestorDashboard(),


            loadCopyTradingDashboard(),


            loadEquity(),


            loadAnalytics(),


            loadTrades(),


            loadMonthly(),


            loadMT5(),


            loadPositions(),


            loadHistory()


        ]);


    }


    catch(error){


        console.error(

            "Dashboard Loading Error:",

            error

        );


    }


}







// ======================================
// APPLICATION START
// ======================================


window.addEventListener(

    "load",

    ()=>{


        // Check authentication


        if(

            !requireLogin()

        ){


            return;


        }




        // Initial dashboard load


        loadDashboard();





        // Auto refresh every 30 seconds


        setInterval(

            loadDashboard,

            REFRESH_INTERVAL

        );


    }

);


