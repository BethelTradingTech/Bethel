import { useState } from "react";
import { Link } from "react-router-dom";
import { registerSubscriber } from "../../services/auth";

export default function Register() {
  const [form, setForm] = useState({
    name: "",
    email: "",
    password: "",
    confirmPassword: ""
  });
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    if (form.password !== form.confirmPassword) {
      setError("Passwords do not match");
      return;
    }
    setSubmitting(true);
    try {
      const result = await registerSubscriber(
        form.name.trim(),
        form.email.trim().toLowerCase(),
        form.password
      );
      setMessage(
        result.message ||
          "Account created. Check your email and verify it before signing in."
      );
      setForm({ name: "", email: form.email, password: "", confirmPassword: "" });
    } catch (requestError) {
      setError(
        requestError.response?.data?.detail ||
          "Registration could not be completed"
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="onboarding-shell">
      <form className="onboarding-card" onSubmit={submit}>
        <p className="eyebrow">Public subscriber registration</p>
        <h1>Create your Bethel account</h1>
        <p>Register directly, then verify your email before continuing onboarding.</p>
        <label>Full name</label>
        <input
          type="text"
          minLength="2"
          maxLength="100"
          required
          value={form.name}
          onChange={(event) => setForm({ ...form, name: event.target.value })}
        />
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
          minLength="12"
          required
          value={form.password}
          onChange={(event) => setForm({ ...form, password: event.target.value })}
        />
        <small>Use uppercase, lowercase, a number and a special character.</small>
        <label>Confirm password</label>
        <input
          type="password"
          minLength="12"
          required
          value={form.confirmPassword}
          onChange={(event) =>
            setForm({ ...form, confirmPassword: event.target.value })
          }
        />
        <button disabled={submitting}>
          {submitting ? "Creating account…" : "Register and verify email"}
        </button>
        {message && <p className="form-success">{message}</p>}
        {error && <p className="form-error">{error}</p>}
        <p>Already verified? <Link to="/login">Sign in</Link></p>
      </form>
    </main>
  );
}
