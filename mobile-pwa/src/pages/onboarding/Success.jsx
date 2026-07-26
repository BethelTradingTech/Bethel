import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { getOnboardingStatus } from "../../services/api";
import { getSubscriberId } from "../../services/auth";

export default function Success() {
  const [status, setStatus] = useState(null);

  useEffect(() => {
    getOnboardingStatus(getSubscriberId()).then(setStatus);
  }, []);

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <p className="success-mark">✓</p>
        <h1>Setup received</h1>
        <p>Your subscription, payment, KYC, broker, and approval checks must be completed before copy trading activates.</p>
        {status && (
          <ul className="status-list">
            <li>Subscription: {status.subscription_status}</li>
            <li>KYC: {status.kyc_status}</li>
            <li>Payment: {status.payment_status}</li>
            <li>Broker: {status.broker_status}</li>
            <li>Approval: {status.admin_approval}</li>
          </ul>
        )}
        <Link className="button-link" to="/">Open dashboard</Link>
      </section>
    </main>
  );
}
