async function loadDashboard(){


    // =========================
    // MT5 STATUS
    // =========================

    const mt5 = await apiGet(
        "/investor/api/mt5"
    );


    document.getElementById(
        "mt5-status"
    ).innerText =
    mt5
        ? (mt5.status || "offline").toUpperCase()
        : "API UNAVAILABLE";



    // =========================
    // EQUITY / BALANCE
    // =========================

    const equity = await apiGet(
        "/performance/equity-history"
    );


    if(
        equity &&
        equity.history &&
        equity.history.length
    ){

        const latest =
        equity.history[
            equity.history.length - 1
        ];


        document.getElementById(
            "balance"
        ).innerText =
        "$" + Number(
            latest.balance
        ).toFixed(2);



        document.getElementById(
            "equity"
        ).innerText =
        "$" + Number(
            latest.equity
        ).toFixed(2);

    }



    // =========================
    // PERFORMANCE
    // =========================

    const performance = await apiGet(
        "/performance/analytics"
    );


    if(performance){


        document.getElementById(
            "return"
        ).innerText =
        performance.total_return_percent + "%";



        document.getElementById(
            "winrate"
        ).innerText =
        performance.win_rate + "%";



        document.getElementById(
            "profit-factor"
        ).innerText =
        performance.profit_factor;



        document.getElementById(
            "risk"
        ).innerText =
        performance.risk_level;


    }




    // =========================
    // COPY TRADING
    // =========================

    const copy = await apiGet(
        "/copytrading/dashboard"
    );


    if(copy){


        document.getElementById(
            "subscribers"
        ).innerText =
        copy.subscribers.total;



        document.getElementById(
            "master-trades"
        ).innerText =
        copy.trading.master_trades;



        document.getElementById(
            "copy-trades"
        ).innerText =
        copy.trading.copy_orders;



        document.getElementById(
            "executed-orders"
        ).innerText =
        copy.trading.executed_orders;


    }




    // =========================
    // OPEN POSITIONS
    // =========================

    const positions = await apiGet(
        "/mt5/positions"
    );


    if(
        positions &&
        positions.positions
    ){


        const list =
        positions.positions;



        document.getElementById(
            "positions"
        ).innerText =
        list.length;



        const table =
        document.getElementById(
            "positions-table"
        );


        table.innerHTML = "";



        list.forEach(pos=>{


            table.innerHTML += `

            <tr>

            <td>${pos.symbol}</td>

            <td>${pos.type}</td>

            <td>${pos.volume}</td>

            <td>${pos.profit}</td>

            </tr>

            `;


        });


    }

    await loadInvestors();

}


function formatMoney(value){

    return Number(value || 0).toLocaleString(
        undefined,
        {
            style: "currency",
            currency: "USD"
        }
    );

}


function addDetailRow(list, label, value){

    const term = document.createElement("dt");
    term.textContent = label;

    const description = document.createElement("dd");
    description.textContent = value ?? "--";

    list.append(term, description);

}


async function showInvestor(investorId){

    const investor = await apiGet(
        "/admin/investors/" + investorId
    );

    if(!investor){
        return;
    }

    const detail = document.getElementById("investor-detail");
    detail.replaceChildren();

    const heading = document.createElement("h3");
    heading.textContent = investor.name;

    const list = document.createElement("dl");
    addDetailRow(list, "Email", investor.email);
    addDetailRow(list, "Country", investor.country);
    addDetailRow(list, "Status", investor.status);
    addDetailRow(
        list,
        "Portfolio",
        investor.portfolio?.name
    );
    addDetailRow(
        list,
        "Current value",
        formatMoney(investor.portfolio?.current_value)
    );
    addDetailRow(
        list,
        "MT5 account",
        investor.mt5?.login
    );
    addDetailRow(list, "MT5 server", investor.mt5?.server);

    detail.append(heading, list);

}


async function loadInvestors(){

    const data = await apiGet("/admin/investors");

    if(!data || !Array.isArray(data.investors)){
        return;
    }

    const table = document.getElementById("investors-table");
    table.replaceChildren();

    data.investors.forEach(investor => {

        const row = document.createElement("tr");

        [
            investor.name,
            investor.email,
            investor.status,
            formatMoney(investor.portfolio?.current_value)
        ].forEach(value => {
            const cell = document.createElement("td");
            cell.textContent = value ?? "--";
            row.appendChild(cell);
        });

        const actionCell = document.createElement("td");
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = "View";
        button.addEventListener(
            "click",
            () => showInvestor(investor.id)
        );
        actionCell.appendChild(button);
        row.appendChild(actionCell);
        table.appendChild(row);

    });

}



if(isAuthenticated()){

    loadDashboard();

    setInterval(
        loadDashboard,
        30000
    );

}
