const API_URL = window.location.origin;
let equityChart = null;
let analyticsTimer = null;

async function fetchAPI(endpoint) {
  try {
    const separator = endpoint.includes("?") ? "&" : "?";
    const response = await fetch(`${API_URL}${endpoint}${separator}t=${Date.now()}`, {
      method: "GET",
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (response.redirected) {
      window.location.href = "/login";
      return {};
    }
    if (!response.ok) throw new Error(`${endpoint} failed (${response.status})`);
    return await response.json();
  } catch (error) {
    console.error("API ERROR:", endpoint, error);
    return {};
  }
}

function updateElement(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

function money(value) {
  return `$${Number(value || 0).toFixed(2)}`;
}

function percent(value, digits = 2) {
  return `${Number(value || 0).toFixed(digits)}%`;
}

function number(value, digits = 2) {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed.toFixed(digits) : "0.00";
}

function direction(type) {
  return Number(type) === 0 ? "BUY" : "SELL";
}

async function loadAccountAndPositions() {
  const data = await fetchAPI("/dashboard/data");
  const account = data.account || {};
  const positions = data.positions || {};

  updateElement("status", data.account ? "MT5 Status: ONLINE" : "MT5 Status: ERROR");
  updateElement("balance", money(account.balance));
  updateElement("equity", money(account.equity));
  updateElement("profit", money(account.profit));
  updateElement("login", account.login || "-");
  updateElement("server", account.server || "-");
  updateElement("currency", account.currency || "-");
  updateElement("leverage", account.leverage || "-");
  updateElement("positions", positions.count || 0);

  const table = document.getElementById("positions-table");
  if (table) {
    table.innerHTML = (positions.positions || []).map((position) => `
      <tr>
        <td>${String(position.symbol || "-")}</td>
        <td>${direction(position.type)}</td>
        <td>${Number(position.volume || 0)}</td>
        <td>${money(position.profit)}</td>
      </tr>`).join("");
  }
}

async function loadAnalytics() {
  const [unified, legacy, riskData] = await Promise.all([
    fetchAPI("/performance/analytics"),
    fetchAPI("/analytics/performance"),
    fetchAPI("/risk/status"),
  ]);

  const legacyPerformance = legacy.performance || {};
  const analytics = unified && unified.status !== "error" && Object.keys(unified).length
    ? unified
    : legacyPerformance;
  const risk = riskData.risk || {};

  updateElement("total-return", percent(analytics.total_return_percent));
  updateElement("daily-return", percent(analytics.daily_return_percent, 4));
  updateElement("monthly-return", percent(analytics.monthly_return_percent));
  updateElement("total-trades", analytics.total_trades ?? legacyPerformance.total_trades ?? 0);
  updateElement("winning-trades", analytics.winning_trades ?? legacyPerformance.winning_trades ?? 0);
  updateElement("losing-trades", analytics.losing_trades ?? legacyPerformance.losing_trades ?? 0);
  updateElement("win-rate", percent(analytics.win_rate ?? legacyPerformance.win_rate));
  updateElement("profit-factor", number(analytics.profit_factor ?? legacyPerformance.profit_factor));
  updateElement("total-profit", money(analytics.total_profit ?? legacyPerformance.total_profit));
  updateElement("performance-grade", analytics.performance_grade || "-");
  updateElement("sharpe-ratio", number(analytics.sharpe_ratio));
  updateElement("sortino-ratio", number(analytics.sortino_ratio));
  updateElement("recovery-factor", analytics.recovery_factor == null ? "N/A" : number(analytics.recovery_factor));
  updateElement("consistency-score", percent(analytics.consistency_score));
  updateElement("volatility", percent(analytics.volatility));
  updateElement("max-drawdown", percent(analytics.maximum_drawdown_percent ?? risk.drawdown_percent));
  updateElement("risk-level", analytics.risk_level || risk.level || "-");
  updateElement("risk-score", `${Number(risk.risk_score || 0).toFixed(1)}/10`);
}

async function loadEquity() {
  const stored = await fetchAPI("/performance/equity-history");
  const legacy = Object.keys(stored).length ? {} : await fetchAPI("/analytics/equity");
  const history = stored.history || legacy.equity?.equity_curve || [];
  if (history.length) updateEquityChart(history);
}

async function loadHistory() {
  const historyData = await fetchAPI("/mt5/history");
  const table = document.getElementById("history-table");
  if (!table) return;
  table.innerHTML = (historyData.history || []).slice(0, 50).map((trade) => `
    <tr>
      <td>${String(trade.symbol || "-")}</td>
      <td>${direction(trade.type)}</td>
      <td>${Number(trade.volume || 0)}</td>
      <td>${money(trade.profit)}</td>
      <td>${trade.time ? new Date(trade.time).toLocaleString() : "-"}</td>
    </tr>`).join("");
}

function updateEquityChart(history) {
  const canvas = document.getElementById("equityChart");
  if (!canvas || typeof Chart === "undefined") return;
  const labels = history.map((item) => new Date(item.timestamp || item.time).toLocaleString());
  const values = history.map((item) => Number(item.equity || 0));
  if (equityChart) {
    equityChart.data.labels = labels;
    equityChart.data.datasets[0].data = values;
    equityChart.update();
    return;
  }
  equityChart = new Chart(canvas, {
    type: "line",
    data: { labels, datasets: [{ label: "Account Equity", data: values, tension: 0.3 }] },
    options: { responsive: true, maintainAspectRatio: false },
  });
}

async function loadDashboard() {
  await Promise.all([loadAccountAndPositions(), loadAnalytics(), loadEquity(), loadHistory()]);
}

loadDashboard();
setInterval(loadAccountAndPositions, 10000);
setInterval(loadAnalytics, 60000);
setInterval(loadHistory, 60000);
setInterval(loadEquity, 300000);
