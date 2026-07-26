import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { registerSubscriber } from "../../services/auth";

export default function Register() {
  const navigate = useNavigate();
  const [form, setForm] = useState({
    email: "",
    password: "",
    confirmPassword: ""
  });
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setError("");
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    try {
      await registerSubscriber(form.email, form.password);
      navigate("/login");
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Your investor invitation could not be found"
      );
    }
  }

  return (
    <main className="onboarding-shell">
      <form className="onboarding-card" onSubmit={submit}>
        <p className="eyebrow">Invitation required</p>
        <h1>Create your password</h1>
        <p>Use the email address registered by Bethel.</p>
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
          minLength="10"
          required
          value={form.password}
          onChange={(event) => setForm({ ...form, password: event.target.value })}
        />
        <label>Confirm password</label>
        <input
          type="password"
          required
          value={form.confirmPassword}
          onChange={(event) =>
            setForm({ ...form, confirmPassword: event.target.value })
          }
        />
        <button>Create account</button>
        {error && <p className="form-error">{error}</p>}
        <p>Already registered? <Link to="/login">Sign in</Link></p>
      </form>
    </main>
  );
}
