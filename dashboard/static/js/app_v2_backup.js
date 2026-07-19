const API_URL = "http://127.0.0.1:8000";


let equityChart = null;



async function loadDashboard() {


    try {



        // ======================
        // DASHBOARD DATA
        // ======================


        const response = await fetch(
            API_URL +
            "/dashboard/data?t=" +
            Date.now()
        );


        const data = await response.json();



        console.log(
            "Dashboard:",
            data
        );





        // ======================
        // MT5 STATUS
        // ======================


        document.getElementById("status").innerHTML =
            "MT5 Status: " +
            (
                data.system?.status ||
                "OFFLINE"
            ).toUpperCase();







        // ======================
        // ACCOUNT DATA
        // ======================


        const account =
            data.account || {};



        document.getElementById("balance").innerHTML =
            "$" +
            Number(account.balance || 0)
            .toFixed(2);



        document.getElementById("equity").innerHTML =
            "$" +
            Number(account.equity || 0)
            .toFixed(2);



        document.getElementById("profit").innerHTML =
            "$" +
            Number(account.profit || 0)
            .toFixed(2);







        // ======================
        // OPEN POSITIONS
        // ======================


        const positions =
            data.positions || {};



        document.getElementById("positions").innerHTML =
            positions.count || 0;




        const table =
            document.getElementById(
                "positions-table"
            );



        table.innerHTML = "";




        (positions.positions || [])
        .forEach(position => {



            table.innerHTML += `

            <tr>

                <td>
                    ${position.symbol || "-"}
                </td>


                <td>

                    ${
                        position.type === 0
                        ? "BUY"
                        : "SELL"

                    }

                </td>



                <td>
                    ${position.volume || 0}
                </td>



                <td>
                    $${Number(
                        position.profit || 0
                    ).toFixed(2)}
                </td>



            </tr>

            `;


        });









        // ======================
        // PERFORMANCE ANALYTICS
        // ======================



        const analyticsResponse =
            await fetch(

                API_URL +
                "/analytics/performance?t=" +
                Date.now()

            );



        const analytics =
            await analyticsResponse.json();



        const performance =
            analytics.performance || {};




        document.getElementById("total-trades").innerHTML =
            performance.total_trades || 0;



        document.getElementById("winning-trades").innerHTML =
            performance.winning_trades || 0;



        document.getElementById("losing-trades").innerHTML =
            performance.losing_trades || 0;



        document.getElementById("win-rate").innerHTML =
            (performance.win_rate || 0)
            + "%";



        document.getElementById("profit-factor").innerHTML =
            performance.profit_factor || 0;



        document.getElementById("total-profit").innerHTML =
            "$" +
            Number(
                performance.total_profit || 0
            )
            .toFixed(2);









        // ======================
        // RISK ENGINE
        // ======================



        const riskResponse =
            await fetch(

                API_URL +
                "/risk/status?t=" +
                Date.now()

            );



        const riskData =
            await riskResponse.json();



        const risk =
            riskData.risk || {};





        document.getElementById("risk-level").innerHTML =
            risk.level || "-";



        document.getElementById("drawdown").innerHTML =
            (risk.drawdown_percent || 0)
            + "%";



        document.getElementById("risk-open-positions").innerHTML =
            risk.open_positions || 0;



        document.getElementById("risk-score").innerHTML =
            (risk.risk_score || 0)
            + "/10";









        // ======================
        // EQUITY CURVE
        // ======================



        const equityResponse =
            await fetch(

                API_URL +
                "/analytics/equity?t=" +
                Date.now()

            );



        const equityData =
            await equityResponse.json();




        updateEquityChart(
            equityData.equity_curve || []
        );



    }



    catch(error) {



        console.error(
            "Dashboard Error:",
            error
        );



        document.getElementById("status").innerHTML =
            "MT5 Status: ERROR";


    }


}









// ======================
// EQUITY CHART
// ======================


function updateEquityChart(data) {


    const canvas =
        document.getElementById(
            "equityChart"
        );



    if(!canvas){

        return;

    }



    const labels =
        data.map(
            item =>
            new Date(
                item.time
            )
            .toLocaleDateString()
        );



    const values =
        data.map(
            item =>
            item.equity
        );





    if(equityChart){


        equityChart.data.labels =
            labels;


        equityChart.data.datasets[0].data =
            values;


        equityChart.update();


        return;

    }







    equityChart =
    new Chart(

        canvas,


        {

            type:"line",


            data:{


                labels:labels,


                datasets:[

                    {

                        label:
                        "Equity",

                        data:
                        values,


                        tension:0.3

                    }

                ]


            },


            options:{


                responsive:true,


                plugins:{


                    legend:{


                        display:true


                    }


                }



            }



        }


    );


}









// Initial Load

loadDashboard();



// Auto Refresh

setInterval(

    loadDashboard,

    5000

);