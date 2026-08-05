import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { verifySubscriberEmail } from "../../services/auth";

export default function VerifyEmail() {
  const [searchParams] = useSearchParams();
  const [state, setState] = useState({ loading: true, error: "", message: "" });

  useEffect(() => {
    const token = searchParams.get("token");
    if (!token) {
      setState({ loading: false, error: "The verification link is incomplete.", message: "" });
      return;
    }
    verifySubscriberEmail(token)
      .then((result) =>
        setState({ loading: false, error: "", message: result.message || "Email verified." })
      )
      .catch((requestError) =>
        setState({
          loading: false,
          error: requestError.response?.data?.detail || "The verification link is invalid or expired.",
          message: ""
        })
      );
  }, [searchParams]);

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <p className="eyebrow">Email verification</p>
        <h1>Verify your Bethel account</h1>
        {state.loading && <p>Verifying your email…</p>}
        {state.message && <p className="form-success">{state.message}</p>}
        {state.error && <p className="form-error">{state.error}</p>}
        {!state.loading && !state.error && (
          <Link className="button-link" to="/login">Continue to sign in</Link>
        )}
        {!state.loading && state.error && (
          <p>Return to <Link to="/register">registration</Link> to request another verification email.</p>
        )}
      </section>
    </main>
  );
}
