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


function money(value, currency = "USD"){
    const n = Number(value);
    if(!Number.isFinite(n)) return "--";
    try {
        return n.toLocaleString(undefined, {style: "currency", currency});
    } catch(_error) {
        return n.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2}) + " " + currency;
    }
}


function percent(value){
    const n = Number(value);
    return Number.isFinite(n) ? `${n.toFixed(2)}%` : "--";
}


function renderPublicHistory(points){
    const container = document.querySelector(".chart-container");
    if(!container) return;
    const clean = (Array.isArray(points) ? points : []).filter(
        point => Number.isFinite(Number(point.balance)) && Number.isFinite(Number(point.equity))
    );
    if(clean.length < 2){
        container.innerHTML = "<p>Verified balance and equity history will appear here as additional public snapshots become available.</p>";
        return;
    }

    const width = 900;
    const height = 260;
    const pad = 18;
    const values = clean.flatMap(point => [Number(point.balance), Number(point.equity)]);
    let min = Math.min(...values);
    let max = Math.max(...values);
    if(max === min){ max += 1; min -= 1; }
    const x = index => pad + (index * (width - pad * 2) / (clean.length - 1));
    const y = value => height - pad - ((value - min) * (height - pad * 2) / (max - min));
    const line = key => clean.map((point, index) => `${index ? "L" : "M"}${x(index).toFixed(1)},${y(Number(point[key])).toFixed(1)}`).join(" ");

    container.innerHTML = `
        <svg viewBox="0 0 ${width} ${height}" role="img" aria-label="Public balance and equity history" style="width:100%;height:260px;display:block">
            <path d="${line("balance")}" fill="none" stroke="currentColor" stroke-width="2" opacity="0.65" vector-effect="non-scaling-stroke"></path>
            <path d="${line("equity")}" fill="none" stroke="#10b981" stroke-width="3" vector-effect="non-scaling-stroke"></path>
        </svg>
        <p style="margin-top:.75rem">Read-only active-master balance and equity history · ${clean.length} sampled points.</p>`;
}


function setPublicTradeHistoryMessage(){
    const body = document.querySelector("#historyTable tbody");
    if(!body) return;
    body.innerHTML = '<tr><td colspan="5">Detailed investor-specific trade history remains private. Public visitors can explore the sanitized live performance record above.</td></tr>';
}


async function loadPublicExplorer(){
    const actionButton = document.getElementById("logout-button");
    if(actionButton){
        actionButton.textContent = "Investor Sign In";
        actionButton.onclick = () => window.location.href = "login.html";
    }

    safe("status", "PUBLIC READ-ONLY");
    safe("investorName", "Public Investor & Partner View");
    safe("portfolioName", "Bethel Active Master · Read Only");
    setPublicTradeHistoryMessage();

    try {
        const [summaryResponse, historyResponse] = await Promise.all([
            fetch(API + "/performance/public-summary?ts=" + Date.now(), {cache: "no-store", headers: {"Accept": "application/json"}}),
            fetch(API + "/performance/public-history?ts=" + Date.now(), {cache: "no-store", headers: {"Accept": "application/json"}})
        ]);
        if(!summaryResponse.ok) throw new Error("Public performance unavailable");
        const summary = await summaryResponse.json();
        if(!summary.available) throw new Error("Public performance unavailable");

        const currency = summary.currency || "USD";
        safe("balance", money(summary.current_balance, currency));
        safe("currentEquity", money(summary.current_equity, currency));
        safe("profit", percent(summary.total_return_percent));
        safe("drawdown", percent(summary.current_drawdown_percent ?? summary.maximum_drawdown_percent));
        safe("sharpe", Number.isFinite(Number(summary.sharpe_ratio)) ? Number(summary.sharpe_ratio).toFixed(2) : "--");
        safe("profitfactor", Number.isFinite(Number(summary.profit_factor)) ? Number(summary.profit_factor).toFixed(2) : "--");
        safe("volatility", percent(summary.annualized_volatility_percent));
        safe("status", "PUBLIC VERIFIED");

        if(historyResponse.ok){
            const history = await historyResponse.json();
            renderPublicHistory(history && Array.isArray(history.points) ? history.points : []);
        } else {
            renderPublicHistory([]);
        }
    } catch(error) {
        safe("status", "PUBLIC DATA UNAVAILABLE");
        safe("balance", "--");
        safe("currentEquity", "--");
        safe("profit", "--");
        safe("drawdown", "--");
        renderPublicHistory([]);
    }
}


async function loadPrivateInvestorDashboard(session){
    const actionButton = document.getElementById("logout-button");
    if(actionButton){
        actionButton.textContent = "Log out";
        actionButton.onclick = investorLogout;
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
            await loadPublicExplorer();
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


async function loadInvestorDashboard(){
    const session = getInvestorSession();
    if(session){
        await loadPrivateInvestorDashboard(session);
    } else {
        await loadPublicExplorer();
    }
}


loadInvestorDashboard();
setInterval(loadInvestorDashboard, 30000);
