const API_URL = window.location.origin;
let equityHistory = [];

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

const money = (value) => `$${Number(value || 0).toFixed(2)}`;
const percent = (value, digits = 2) => `${Number(value || 0).toFixed(digits)}%`;
const number = (value, digits = 2) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : "0.00";
const direction = (type) => Number(type) === 0 ? "BUY" : "SELL";

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
  if (table) table.innerHTML = (positions.positions || []).map((position) => `
    <tr><td>${String(position.symbol || "-")}</td><td>${direction(position.type)}</td><td>${Number(position.volume || 0)}</td><td>${money(position.profit)}</td></tr>
  `).join("");
}

async function loadAnalytics() {
  const [unified, legacy, riskData] = await Promise.all([
    fetchAPI("/performance/analytics"),
    fetchAPI("/analytics/performance"),
    fetchAPI("/risk/status"),
  ]);
  const legacyPerformance = legacy.performance || {};
  const analytics = unified && unified.status !== "error" && Object.keys(unified).length ? unified : legacyPerformance;
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
  equityHistory = stored.history || legacy.equity?.equity_curve || [];
  drawEquityChart();
}

async function loadHistory() {
  const historyData = await fetchAPI("/mt5/history");
  const table = document.getElementById("history-table");
  if (!table) return;
  table.innerHTML = (historyData.history || []).slice(0, 50).map((trade) => `
    <tr><td>${String(trade.symbol || "-")}</td><td>${direction(trade.type)}</td><td>${Number(trade.volume || 0)}</td><td>${money(trade.profit)}</td><td>${trade.time ? new Date(trade.time).toLocaleString() : "-"}</td></tr>
  `).join("");
}

function drawEquityChart() {
  const canvas = document.getElementById("equityChart");
  if (!canvas || !equityHistory.length) return;
  const width = canvas.clientWidth || 900;
  const height = Number(canvas.getAttribute("height")) || 320;
  const scale = window.devicePixelRatio || 1;
  canvas.width = width * scale;
  canvas.height = height * scale;
  const ctx = canvas.getContext("2d");
  ctx.scale(scale, scale);
  ctx.clearRect(0, 0, width, height);

  const values = equityHistory.map((item) => Number(item.equity || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = Math.max(max - min, 1);
  const pad = 32;

  ctx.strokeStyle = "rgba(148, 163, 184, 0.35)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 4; i += 1) {
    const y = pad + ((height - pad * 2) * i / 4);
    ctx.beginPath(); ctx.moveTo(pad, y); ctx.lineTo(width - pad, y); ctx.stroke();
  }

  ctx.strokeStyle = "#22c55e";
  ctx.lineWidth = 2;
  ctx.beginPath();
  values.forEach((value, index) => {
    const x = pad + ((width - pad * 2) * index / Math.max(values.length - 1, 1));
    const y = height - pad - ((value - min) / range) * (height - pad * 2);
    if (index === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#94a3b8";
  ctx.font = "12px sans-serif";
  ctx.fillText(money(max), pad, 18);
  ctx.fillText(money(min), pad, height - 8);
}

async function loadDashboard() {
  await Promise.all([loadAccountAndPositions(), loadAnalytics(), loadEquity(), loadHistory()]);
}

window.addEventListener("resize", drawEquityChart);
loadDashboard();
setInterval(loadAccountAndPositions, 10000);
setInterval(loadAnalytics, 60000);
setInterval(loadHistory, 60000);
setInterval(loadEquity, 300000);
