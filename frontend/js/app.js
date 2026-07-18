const API_URL = "https://api.betheltradingtechnologies.com";


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


        console.log(data);



        // SYSTEM STATUS

        document.getElementById("status").innerHTML =
            "MT5 Status: " +
            (data.system?.status || "UNKNOWN").toUpperCase();



        // ACCOUNT DATA

        const account = data.account || {};



        document.getElementById("login").innerHTML =
            account.login || "-";


        document.getElementById("server").innerHTML =
            account.server || "-";


        document.getElementById("currency").innerHTML =
            account.currency || "-";



        // MONEY DATA


        document.getElementById("balance").innerHTML =
            "$" + Number(account.balance || 0).toFixed(2);



        document.getElementById("equity").innerHTML =
            "$" + Number(account.equity || 0).toFixed(2);



        document.getElementById("profit").innerHTML =
            "$" + Number(account.profit || 0).toFixed(2);





        // POSITIONS


        const positions =
            data.positions || {};



        document.getElementById("positions").innerHTML =
            positions.count || 0;



        const table =
            document.getElementById(
                "positions-table"
            );


        table.innerHTML = "";



        const list =
            positions.positions || [];



        list.forEach(position => {


            table.innerHTML += `

            <tr>

                <td>${position.symbol || "-"}</td>

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



loadDashboard();


setInterval(
    loadDashboard,
    5000
);