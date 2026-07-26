import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { getPlans, selectPlan } from "../../services/api";
import { getSubscriberId } from "../../services/auth";

export default function Subscription() {
  const navigate = useNavigate();
  const [plans, setPlans] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    getPlans().then(setPlans).catch(() => setError("Plans are unavailable"));
  }, []);

  async function choose(planId) {
    try {
      await selectPlan(getSubscriberId(), planId);
      navigate("/connect-mt5");
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to select plan");
    }
  }

  return (
    <main className="onboarding-shell">
      <section className="onboarding-card">
        <p className="eyebrow">Step 1 of 2</p>
        <h1>Choose subscription</h1>
        {plans.map((plan) => (
          <article className="plan-card" key={plan.id}>
            <h2>{plan.name}</h2>
            <strong>${plan.price} {plan.currency} / month</strong>
            <p>{plan.description}</p>
            <button onClick={() => choose(plan.id)}>Choose plan</button>
          </article>
        ))}
        {error && <p className="form-error">{error}</p>}
      </section>
    </main>
  );
}
