/*
Bethel Trading Technologies
Live Dashboard Controller
*/


async function loadDashboard(){

    try{


        const response = await fetch(
            "/dashboard/data"
        );


        const data = await response.json();



        document.getElementById(
            "status"
        ).innerHTML =
        "MT5 Status: " + data.system.status;



        if(data.account){


            document.getElementById(
                "balance"
            ).innerHTML =
            "$" + data.account.balance.toFixed(2);



            document.getElementById(
                "equity"
            ).innerHTML =
            "$" + data.account.equity.toFixed(2);



            document.getElementById(
                "profit"
            ).innerHTML =
            "$" + data.account.profit.toFixed(2);


        }



        if(data.positions){


            document.getElementById(
                "positions"
            ).innerHTML =
            data.positions.count;



            let rows = "";



            data.positions.positions.forEach(
                position => {


                let type = 
                position.type === 0
                ? "BUY"
                : "SELL";



                rows += `

                <tr>

                <td>${position.symbol}</td>

                <td>${type}</td>

                <td>${position.volume}</td>

                <td>${position.profit}</td>

                </tr>

                `;


            });



            document.getElementById(
                "positions-table"
            ).innerHTML = rows;


        }


    }


    catch(error){


        console.log(
            "Dashboard Error:",
            error
        );


        document.getElementById(
            "status"
        ).innerHTML =
        "MT5 Status: OFFLINE";


    }


}



setInterval(
    loadDashboard,
    5000
);



loadDashboard();