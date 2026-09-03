import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { connectMT5 } from "../../services/api";
import { getSubscriberId } from "../../services/auth";

export default function ConnectMT5() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    broker: "",
    mt5_account: "",
    server: "",
    account_type: "STANDARD",
    starting_capital_usd: ""
  });
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await connectMT5(getSubscriberId(), form);
      navigate("/onboarding-success");
    } catch (requestError) {
      const detail = requestError.response?.data?.detail;
      setError(
        typeof detail === "string"
          ? detail
          : "Unable to connect MT5 account. Check the account details and try again."
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="onboarding-shell">
      <form className="onboarding-card" onSubmit={submit}>
        <p className="eyebrow">Trading account connection</p>
        <h1>Connect MT5</h1>
        <p>
          Add the trading account that will receive Bethel copy-trading signals.
          Do not enter your MT5 trading password here.
        </p>

        <label>Broker</label>
        <input
          required
          autoComplete="organization"
          placeholder="HF Markets"
          value={form.broker}
          onChange={(event) => update("broker", event.target.value)}
        />

        <label>MT5 account number</label>
        <input
          required
          inputMode="numeric"
          autoComplete="off"
          placeholder="12345678"
          value={form.mt5_account}
          onChange={(event) => update("mt5_account", event.target.value)}
        />

        <label>Broker server</label>
        <input
          required
          autoComplete="off"
          placeholder="HFMarketsGlobal-Demo"
          value={form.server}
          onChange={(event) => update("server", event.target.value)}
        />

        <label>Account type</label>
        <select
          value={form.account_type}
          onChange={(event) => update("account_type", event.target.value)}
        >
          <option value="STANDARD">Standard</option>
          <option value="CENT">Cent</option>
        </select>

        <label>Starting capital (USD equivalent)</label>
        <input
          required
          min="0.01"
          step="0.01"
          type="number"
          inputMode="decimal"
          placeholder={form.account_type === "CENT" ? "100" : "1000"}
          value={form.starting_capital_usd}
          onChange={(event) => update("starting_capital_usd", event.target.value)}
        />

        <p>
          Bethel will verify this account through the authorized copier terminal.
          Live trading remains disabled until the required approvals are complete.
        </p>

        <button disabled={submitting}>
          {submitting ? "Connecting…" : "Connect account"}
        </button>
        {error && <p className="form-error">{error}</p>}
      </form>
    </main>
  );
}
