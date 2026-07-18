const API_URL = "https://api.betheltradingtechnologies.com";


async function loadDashboard() {

    try {

        const response = await fetch(
            API_URL + "/dashboard/data?t=" + new Date().getTime()
        );


        if (!response.ok) {

            throw new Error(
                "API Error: " + response.status
            );

        }


        const data = await response.json();


        console.log(data);



        // ======================
        // MT5 STATUS
        // ======================

        document.getElementById("status").innerHTML =
            "MT5 Status: " +
            (data.system?.status ?? "UNKNOWN").toUpperCase();




        // ======================
        // ACCOUNT DATA
        // ======================

        const account = data.account ?? {};



        document.getElementById("login").innerHTML =
            account.login ?? "-";


        document.getElementById("server").innerHTML =
            account.server ?? "-";


        document.getElementById("currency").innerHTML =
            account.currency ?? "-";


        document.getElementById("leverage").innerHTML =
            account.leverage ?? "-";



        document.getElementById("margin").innerHTML =
            "$" + Number(account.margin ?? 0).toFixed(2);



        document.getElementById("free-margin").innerHTML =
            "$" + Number(account.margin_free ?? 0).toFixed(2);



        document.getElementById("margin-level").innerHTML =
            Number(account.margin_level ?? 0).toFixed(2)
            + "%";



        document.getElementById("balance").innerHTML =
            "$" + Number(account.balance ?? 0).toFixed(2);



        document.getElementById("equity").innerHTML =
            "$" + Number(account.equity ?? 0).toFixed(2);



        document.getElementById("profit").innerHTML =
            "$" + Number(account.profit ?? 0).toFixed(2);





        // ======================
        // POSITION DATA
        // ======================


        const positions =
            data.positions ?? {};



        document.getElementById("positions-count").innerHTML =
            positions.count ?? 0;



        document.getElementById("risk-positions").innerHTML =
            positions.count ?? 0;





        // ======================
        // POSITIONS TABLE
        // ======================


        const table =
            document.getElementById(
                "positions-table"
            );


        table.innerHTML = "";



        const positionList =
            positions.positions ?? [];



        positionList.forEach(position => {


            const row = `

                <tr>

                    <td>${position.symbol ?? "-"}</td>

                    <td>
                        ${
                            position.type === 0
                            ? "BUY"
                            : "SELL"
                        }
                    </td>

                    <td>${position.volume ?? 0}</td>

                    <td>
                        $${Number(
                            position.profit ?? 0
                        ).toFixed(2)}
                    </td>

                </tr>

            `;


            table.innerHTML += row;


        });



    }


    catch(error) {


        console.log(
            "Dashboard Error:",
            error
        );


        document.getElementById("status").innerHTML =
            "MT5 Status: ERROR";


    }


}





// Initial load

loadDashboard();



// Refresh every 5 seconds

setInterval(
    loadDashboard,
    5000
);