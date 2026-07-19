const API_URL = "http://127.0.0.1:8000";


let equityChart = null;



// ======================================
// API HELPER
// ======================================

async function fetchAPI(endpoint){


    try{


        const response = await fetch(

            API_URL +
            endpoint +
            "?t=" +
            Date.now(),

            {

                method:"GET",

                credentials:"include"

            }

        );



        if(response.redirected){

            window.location.href="/login";

            return {};

        }



        if(!response.ok){

            throw new Error(

                endpoint + " failed"

            );

        }



        return await response.json();


    }


    catch(error){


        console.error(

            "API ERROR:",
            endpoint,
            error

        );


        return {};

    }


}





// ======================================
// SAFE UPDATE
// ======================================

function updateElement(id,value){


    const element = document.getElementById(id);


    if(element){

        element.innerHTML=value;

    }

}// ======================================
// LOAD DASHBOARD
// ======================================

async function loadDashboard(){


try{


// ======================================
// DASHBOARD DATA
// ======================================


const data = await fetchAPI(

    "/dashboard/data"

);


console.log(

    "Dashboard Data:",
    data

);




// ======================================
// STATUS
// ======================================


if(data.account){


    updateElement(

        "status",

        "MT5 Status: ONLINE"

    );


}
else{


    updateElement(

        "status",

        "MT5 Status: ERROR"

    );


}





// ======================================
// ACCOUNT DATA
// ======================================


const account = data.account || {};



updateElement(

    "balance",

    "$" + Number(

        account.balance || 0

    ).toFixed(2)

);



updateElement(

    "equity",

    "$" + Number(

        account.equity || 0

    ).toFixed(2)

);



updateElement(

    "profit",

    "$" + Number(

        account.profit || 0

    ).toFixed(2)

);




// ======================================
// MT5 ACCOUNT INFORMATION
// ======================================


updateElement(

    "login",

    account.login || "-"

);



updateElement(

    "server",

    account.server || "-"

);



updateElement(

    "currency",

    account.currency || "-"

);



updateElement(

    "leverage",

    account.leverage || "-"

);





// ======================================
// OPEN POSITIONS COUNT
// ======================================


const positions = data.positions || {};



updateElement(

    "positions",

    positions.count || 0

);


// ======================================
// LIVE POSITIONS TABLE
// ======================================


const positionsTable = document.getElementById(

    "positions-table"

);



if(positionsTable){


    positionsTable.innerHTML = "";



    (positions.positions || []).forEach(position=>{


        positionsTable.innerHTML += `


        <tr>


        <td>${position.symbol}</td>


        <td>

        ${

            position.type === 0

            ?

            "BUY"

            :

            "SELL"

        }

        </td>



        <td>${position.volume}</td>



        <td>

        $${Number(

            position.profit || 0

        ).toFixed(2)}

        </td>


        </tr>


        `;


    });


}







// ======================================
// PERFORMANCE ANALYTICS
// ======================================


const analytics = await fetchAPI(

    "/analytics/performance"

);



const performance = analytics.performance || {};




updateElement(

    "total-trades",

    performance.total_trades || 0

);



updateElement(

    "winning-trades",

    performance.winning_trades || 0

);



updateElement(

    "losing-trades",

    performance.losing_trades || 0

);



updateElement(

    "win-rate",

    (performance.win_rate || 0) + "%"

);



updateElement(

    "profit-factor",

    performance.profit_factor || 0

);



updateElement(

    "total-profit",

    "$" + Number(

        performance.total_profit || 0

    ).toFixed(2)

);

// ======================================
// RISK ENGINE
// ======================================


const riskData = await fetchAPI(

    "/risk/status"

);



const risk = riskData.risk || {};



updateElement(

    "risk-level",

    risk.level || "-"

);



updateElement(

    "drawdown",

    (risk.drawdown_percent || 0) + "%"

);



updateElement(

    "risk-open-positions",

    risk.open_positions || 0

);



updateElement(

    "risk-score",

    (risk.risk_score || 0) + "/10"

);







// ======================================
// EQUITY CURVE DATA
// ======================================


const equityData = await fetchAPI(

    "/analytics/equity"

);



console.log(

    "Equity Data:",

    equityData

);



const equityCurve =

    equityData.equity?.equity_curve || [];



if(equityCurve.length > 0){


    updateEquityChart(

        equityCurve

    );


}








// ======================================
// TRADE HISTORY
// ======================================


const historyData = await fetchAPI(

    "/mt5/history"

);



console.log(

    "History Data:",

    historyData

);



const historyTable = document.getElementById(

    "history-table"

);



if(historyTable){


    historyTable.innerHTML = "";



    (historyData.history || [])

    .slice(0,50)

    .forEach(trade=>{


        historyTable.innerHTML += `


        <tr>


        <td>${trade.symbol}</td>


        <td>

        ${

            trade.type === 0

            ?

            "BUY"

            :

            "SELL"

        }

        </td>



        <td>${trade.volume}</td>



        <td>

        $${Number(

            trade.profit || 0

        ).toFixed(2)}

        </td>



        <td>

        ${

            new Date(

                trade.time

            ).toLocaleString()

        }

        </td>



        </tr>


        `;


    });


}


// ======================================
// EQUITY CHART
// ======================================


function updateEquityChart(history){



const canvas = document.getElementById(

    "equityChart"

);



if(!canvas || history.length === 0){

    return;

}





const labels = history.map(item=>{


    return new Date(

        item.time

    ).toLocaleString();


});





const values = history.map(item=>{


    return item.equity || 0;


});







if(equityChart){


    equityChart.data.labels = labels;


    equityChart.data.datasets[0].data = values;


    equityChart.update();


    return;


}







equityChart = new Chart(

    canvas,

    {


        type:"line",


        data:{


            labels:labels,


            datasets:[

                {


                    label:"Account Equity",


                    data:values,


                    tension:0.3


                }

            ]


        },



        options:{


            responsive:true,


            maintainAspectRatio:false


        }


    }


);



}

// ======================================
// CLOSE LOAD DASHBOARD FUNCTION
// ======================================


}

catch(error){


    console.error(

        "Dashboard Error:",

        error

    );


    updateElement(

        "status",

        "MT5 Status: ERROR"

    );


}


}







// ======================================
// START DASHBOARD
// ======================================


loadDashboard();



setInterval(

    loadDashboard,

    5000

);