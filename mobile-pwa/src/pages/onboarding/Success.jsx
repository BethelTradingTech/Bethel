import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getBrokerAccount, getOnboardingStatus } from "../../services/api";
import { getSubscriberId } from "../../services/auth";

function maskAccount(login) {
  const value = String(login || "");
  if (!value) return "Not linked";
  return value.length <= 4 ? value : `••••${value.slice(-4)}`;
}

export default function Success() {
  const [status, setStatus] = useState(null);
  const [brokerAccount, setBrokerAccount] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    const subscriberId = getSubscriberId();

    async function refresh() {
      try {
        const [onboarding, broker] = await Promise.all([
          getOnboardingStatus(subscriberId),
          getBrokerAccount(subscriberId)
        ]);
        if (!active) return;
        setStatus(onboarding);
        setBrokerAccount(broker?.status === "not_found" ? null : broker);
        setError("");
      } catch (requestError) {
        if (active) {
          setError("Unable to refresh connection status right now.");
        }
      }
    }

    refresh();
    const timer = window.setInterval(refresh, 5000);
    return () => {
      active = false;
      window.clearInterval(timer);
    };
  }, []);

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <p className="success-mark">✓</p>
        <h1>Account connection received</h1>
        <p>
          Bethel is preparing your copier connection. Your trading password is not
          collected by this mobile form.
        </p>

        {brokerAccount && (
          <ul className="status-list">
            <li>Broker: {brokerAccount.broker}</li>
            <li>MT5 account: {maskAccount(brokerAccount.login)}</li>
            <li>Server: {brokerAccount.server}</li>
            <li>Terminal verification: {brokerAccount.status}</li>
            <li>Live authorization: {brokerAccount.live_authorized ? "APPROVED" : "NOT APPROVED"}</li>
          </ul>
        )}

        {status && (
          <ul className="status-list">
            <li>Subscription: {status.subscription_status}</li>
            <li>KYC: {status.kyc_status}</li>
            <li>Payment: {status.payment_status}</li>
            <li>Broker onboarding: {status.broker_status}</li>
            <li>Admin approval: {status.admin_approval}</li>
          </ul>
        )}

        <p>
          If an activation code is required, Bethel sends it separately. Copy trading
          remains inactive until the terminal and all required onboarding checks are approved.
        </p>
        {error && <p className="form-error">{error}</p>}
        <Link className="button-link" to="/">Open dashboard</Link>
      </section>
    </main>
  );
}
