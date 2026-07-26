import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { connectMT5 } from "../../services/api";
import { getSubscriberId } from "../../services/auth";

export default function ConnectMT5() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ broker: "", mt5_account: "" });
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    try {
      await connectMT5(getSubscriberId(), form);
      navigate("/onboarding-success");
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail || "Unable to connect MT5 account"
      );
    }
  }

  return (
    <main className="onboarding-shell">
      <form className="onboarding-card" onSubmit={submit}>
        <p className="eyebrow">Step 2 of 2</p>
        <h1>Connect MT5</h1>
        <label>Broker</label>
        <input
          required
          placeholder="HF Markets"
          value={form.broker}
          onChange={(event) => setForm({ ...form, broker: event.target.value })}
        />
        <label>MT5 account number</label>
        <input
          required
          inputMode="numeric"
          value={form.mt5_account}
          onChange={(event) =>
            setForm({ ...form, mt5_account: event.target.value })
          }
        />
        <button>Continue</button>
        {error && <p className="form-error">{error}</p>}
      </form>
    </main>
  );
}
