const API =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.startsWith("192.168.")
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : window.location.hostname === "bethel-api.onrender.com" ||
          window.location.hostname === "api.betheltradingtechnologies.com"
            ? window.location.origin
            : "https://api.betheltradingtechnologies.com";


function safe(id, value){
    const element = document.getElementById(id);
    if(element){
        element.textContent = value ?? "--";
    }
}


function money(value){
    return Number(value || 0).toLocaleString(
        undefined,
        {style: "currency", currency: "USD"}
    );
}


async function loadInvestorDashboard(){
    const session = getInvestorSession();

    if(!session){
        window.location.replace("login.html");
        return;
    }

    try {
        const response = await fetch(
            API + "/investor/api/dashboard/" + session.investor_id,
            {
                headers: {
                    "Accept": "application/json",
                    "Authorization": "Bearer " + getInvestorToken()
                }
            }
        );

        if(response.status === 401 || response.status === 403){
            clearInvestorToken();
            window.location.replace("login.html");
            return;
        }

        if(!response.ok){
            throw new Error("Dashboard request failed");
        }

        const data = await response.json();
        const portfolio = data.portfolio || {};

        safe("status", "ONLINE");
        safe("investorName", data.investor?.name);
        safe("portfolioName", portfolio.name);
        safe("balance", money(portfolio.capital));
        safe("currentEquity", money(portfolio.current_value));
        safe(
            "profit",
            money(
                Number(portfolio.current_value || 0) -
                Number(portfolio.capital || 0)
            )
        );
        safe("drawdown", "--");
    } catch(error) {
        safe("status", "UNAVAILABLE");
    }
}


document.getElementById("logout-button").addEventListener(
    "click",
    investorLogout
);

loadInvestorDashboard();
setInterval(loadInvestorDashboard, 30000);
