async function loadDashboard() {

    try {

        const response = await fetch(
            "/dashboard/data?t=" + new Date().getTime()
        );

        const data = await response.json();

        console.log(data);


        // ======================
        // MT5 STATUS
        // ======================

        document.getElementById("status").innerHTML =
            "MT5 Status: " +
            data.system.status.toUpperCase();



        // ======================
        // ACCOUNT DATA
        // ======================

        const account = data.account;


        document.getElementById("login").innerHTML =
            account.login ?? "-";


        document.getElementById("server").innerHTML =
            account.server ?? "-";


        document.getElementById("currency").innerHTML =
            account.currency ?? "-";


        document.getElementById("leverage").innerHTML =
            account.leverage ?? "-";


        document.getElementById("margin").innerHTML =
            "$" + Number(account.margin).toFixed(2);


        document.getElementById("free-margin").innerHTML =
            "$" + Number(account.margin_free).toFixed(2);


        document.getElementById("margin-level").innerHTML =
            Number(account.margin_level).toFixed(2) + "%";


        document.getElementById("balance").innerHTML =
            "$" + Number(account.balance).toFixed(2);


        document.getElementById("equity").innerHTML =
            "$" + Number(account.equity).toFixed(2);


        document.getElementById("profit").innerHTML =
            "$" + Number(account.profit).toFixed(2);



        // ======================
        // POSITION DATA
        // ======================

        document.getElementById("positions-count").innerHTML =
            data.positions.count;


        document.getElementById("risk-positions").innerHTML =
            data.positions.count;



        // ======================
        // POSITIONS TABLE
        // ======================

        const table =
            document.getElementById(
                "positions-table"
            );

        table.innerHTML = "";


        data.positions.positions.forEach(position => {

            const row = `
                <tr>
                    <td>${position.symbol}</td>
                    <td>${position.type === 0 ? "BUY" : "SELL"}</td>
                    <td>${position.volume}</td>
                    <td>$${Number(position.profit).toFixed(2)}</td>
                </tr>
            `;

            table.innerHTML += row;

        });

    }

    catch(error) {

        console.log(error);

        document.getElementById("status").innerHTML =
            "MT5 Status: ERROR";

    }

}


loadDashboard();

setInterval(
    loadDashboard,
    5000
);