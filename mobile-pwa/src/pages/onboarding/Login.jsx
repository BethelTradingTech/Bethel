import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { loginSubscriber } from "../../services/auth";

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: "", password: "" });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await loginSubscriber(form.email, form.password);
      navigate("/subscription");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to sign in");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="onboarding-shell">
      <form className="onboarding-card" onSubmit={submit}>
        <p className="eyebrow">Bethel Trading Technologies</p>
        <h1>Investor sign in</h1>
        <label>Email</label>
        <input
          type="email"
          required
          value={form.email}
          onChange={(event) => setForm({ ...form, email: event.target.value })}
        />
        <label>Password</label>
        <input
          type="password"
          required
          value={form.password}
          onChange={(event) => setForm({ ...form, password: event.target.value })}
        />
        <button disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
        {error && <p className="form-error">{error}</p>}
        <p>First visit? <Link to="/register">Create your password</Link></p>
      </form>
    </main>
  );
}
