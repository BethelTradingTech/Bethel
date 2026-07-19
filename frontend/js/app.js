const API_URL = "http://127.0.0.1:8000";


async function loadDashboard() {

    try {

        const response = await fetch(
            API_URL + "/dashboard/data?t=" + Date.now()
        );


        if (!response.ok) {

            throw new Error(
                "API Error: " + response.status
            );

        }


        const data = await response.json();


        console.log("Dashboard Data:", data);



        // =========================
        // SYSTEM STATUS
        // =========================

        document.getElementById("status").innerHTML =
            "MT5 Status: " +
            (
                data.system?.status ||
                data.status ||
                "ONLINE"
            ).toUpperCase();



        // =========================
        // ACCOUNT DATA
        // =========================

        const account = data.account || {};


        document.getElementById("login").innerHTML =
            account.login || "-";


        document.getElementById("server").innerHTML =
            account.server || "-";


        document.getElementById("currency").innerHTML =
            account.currency || "USD";



        // =========================
        // BALANCE / EQUITY / PROFIT
        // =========================

        document.getElementById("balance").innerHTML =
            "$" +
            Number(
                account.balance || 0
            ).toFixed(2);



        document.getElementById("equity").innerHTML =
            "$" +
            Number(
                account.equity || 0
            ).toFixed(2);



        document.getElementById("profit").innerHTML =
            "$" +
            Number(
                account.profit || 0
            ).toFixed(2);




        // =========================
        // POSITIONS
        // =========================

        const positions =
            data.positions || {};



        const positionList =
            positions.positions ||
            positions ||
            [];



        document.getElementById("positions").innerHTML =
            positionList.length;



        const table =
            document.getElementById(
                "positions-table"
            );


        table.innerHTML = "";



        positionList.forEach(position => {


            table.innerHTML += `

            <tr>

                <td>
                    ${position.symbol || "-"}
                </td>


                <td>
                    ${
                        position.type === 0 ||
                        position.type === "BUY"
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



        // =========================
        // ONLINE INDICATOR
        // =========================

        document.getElementById("status").style.display =
            "block";


    }



    catch(error) {


        console.error(
            "Dashboard Error:",
            error
        );


        document.getElementById("status").innerHTML =
            "MT5 Status: OFFLINE";


    }

}



// Initial load

loadDashboard();


// Refresh every 5 seconds

setInterval(
    loadDashboard,
    5000
);