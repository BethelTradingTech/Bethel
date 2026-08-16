(() => {
    "use strict";

    const money = (value, currency = "USD") => {
        const amount = Number(value);
        if (!Number.isFinite(amount)) return `${currency} —`;
        try {
            return new Intl.NumberFormat("en-US", {
                style: "currency",
                currency: String(currency || "USD").toUpperCase(),
                maximumFractionDigits: 2
            }).format(amount);
        } catch (_) {
            return `${String(currency || "USD").toUpperCase()} ${amount.toFixed(2)}`;
        }
    };

    const getPlans = async () => {
        const data = await apiRequest("/onboarding/plans", {headers: subscriberHeaders()});
        return Array.isArray(data) ? data : (data.plans || data.subscription_plans || data.data || []);
    };

    const normalizePlan = plan => ({
        id: Number(plan.id ?? plan.plan_id),
        name: plan.name || plan.plan_name || "Subscription plan",
        description: plan.description || plan.plan_description || "Bethel subscription service.",
        price: plan.price ?? plan.monthly_price ?? plan.amount,
        currency: plan.currency || plan.plan_currency || "USD",
        billing: plan.billing_interval || plan.interval || plan.billing || "MONTHLY",
        status: String(plan.status || "ACTIVE").toUpperCase()
    });

    async function selectPlan(plan, button) {
        if (!plan.id) {
            setMessage("fees-package-message", "This subscription package is not currently selectable.", "error");
            return;
        }
        const buttons = document.querySelectorAll("#fees-package-options button[data-plan-id]");
        buttons.forEach(item => item.disabled = true);
        const originalText = button.textContent;
        button.textContent = "Selecting…";
        setMessage("fees-package-message", `Selecting ${plan.name}…`);
        try {
            await apiRequest(`/onboarding/${subscriberId()}/subscription`, {
                method: "POST",
                headers: subscriberHeaders(true),
                body: JSON.stringify({plan_id: plan.id})
            });
            document.querySelectorAll("#fees-package-options .fees-package-card").forEach(card => card.classList.remove("selected"));
            button.closest(".fees-package-card")?.classList.add("selected");
            document.querySelectorAll("#fees-package-options button[data-plan-id]").forEach(item => {
                item.textContent = Number(item.dataset.planId) === plan.id ? "Selected package" : "Select package";
            });
            const planSelect = document.getElementById("plan-select");
            if (planSelect) planSelect.value = String(plan.id);
            setMessage("fees-package-message", `${plan.name} selected successfully.`, "success");
            await refreshStatus();
        } catch (error) {
            button.textContent = originalText;
            setMessage("fees-package-message", error.message || "Unable to select this package.", "error");
        } finally {
            buttons.forEach(item => item.disabled = false);
        }
    }

    async function loadFeesPackages() {
        const panel = document.getElementById("activation-fee-panel");
        if (!panel || !subscriberToken() || !subscriberId()) return;

        let heading = panel.querySelector(".fees-package-heading");
        let container = document.getElementById("fees-package-options");
        let message = document.getElementById("fees-package-message");
        if (!heading) {
            heading = document.createElement("div");
            heading.className = "fees-package-heading";
            heading.innerHTML = '<h3>Choose your subscription package</h3><p class="muted">Prices below are loaded from Bethel’s current pricing settings. Select the package you want for this account.</p>';
            const terms = panel.querySelector(".profit-share-terms");
            panel.insertBefore(heading, terms || null);
        }
        if (!container) {
            container = document.createElement("div");
            container.id = "fees-package-options";
            container.className = "fees-package-options";
            heading.insertAdjacentElement("afterend", container);
        }
        if (!message) {
            message = document.createElement("p");
            message.id = "fees-package-message";
            message.className = "form-message";
            container.insertAdjacentElement("afterend", message);
        }

        container.innerHTML = '<div class="fees-package-loading">Loading current subscription packages…</div>';
        setMessage("fees-package-message", "");
        try {
            const plans = (await getPlans()).map(normalizePlan).filter(plan => plan.status !== "INACTIVE");
            if (!plans.length) throw new Error("No active subscription packages are currently available.");
            container.replaceChildren();
            plans.forEach(plan => {
                const card = document.createElement("article");
                card.className = "fees-package-card";
                card.innerHTML = `
                    <div class="fees-package-card-head">
                        <div><strong>${plan.name}</strong><span>${plan.description}</span></div>
                        <div class="fees-package-price">${money(plan.price, plan.currency)}<small>${String(plan.billing).replaceAll("_", " ").toLowerCase()}</small></div>
                    </div>
                    <button type="button" data-plan-id="${plan.id}">Select package</button>
                `;
                card.querySelector("button").addEventListener("click", event => selectPlan(plan, event.currentTarget));
                container.appendChild(card);
            });
        } catch (error) {
            container.innerHTML = '<div class="fees-package-loading error">Subscription packages could not be loaded.</div>';
            setMessage("fees-package-message", error.message || "Unable to load subscription packages.", "error");
        }
    }

    const style = document.createElement("style");
    style.textContent = `
        .fees-package-heading{margin:1.1rem 0 .75rem}.fees-package-heading h3{margin:0 0 .35rem;font-size:1.05rem}.fees-package-heading p{margin:0}
        .fees-package-options{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:.8rem;margin:.8rem 0 1rem}
        .fees-package-card{border:1px solid rgba(109,162,215,.24);background:#0c172b;border-radius:12px;padding:1rem;display:flex;flex-direction:column;gap:.9rem;min-height:160px}
        .fees-package-card.selected{border-color:#35bdf3;box-shadow:0 0 0 1px rgba(53,189,243,.3)}
        .fees-package-card-head{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}.fees-package-card-head>div:first-child{display:flex;flex-direction:column;gap:.35rem}.fees-package-card-head span{font-size:.82rem;color:#8fa8c4;line-height:1.4}
        .fees-package-price{font-size:1.08rem;font-weight:800;white-space:nowrap;text-align:right}.fees-package-price small{display:block;margin-top:.2rem;font-size:.68rem;font-weight:600;color:#8fa8c4;text-transform:capitalize}
        .fees-package-card button{margin-top:auto;width:100%}.fees-package-loading{padding:1rem;border:1px dashed rgba(109,162,215,.24);border-radius:10px;color:#8fa8c4}.fees-package-loading.error{color:#ff7b7b}
        @media(max-width:620px){.fees-package-card-head{flex-direction:column}.fees-package-price{text-align:left}}
    `;
    document.head.appendChild(style);

    const originalOpenStep = window.openRegistrationStep;
    if (typeof originalOpenStep === "function") {
        window.openRegistrationStep = function(step, scroll = true) {
            originalOpenStep(step, scroll);
            if (Number(step) === 7) loadFeesPackages();
        };
    }

    document.querySelectorAll(".progress-item").forEach((item, index) => {
        if (index === 4) item.addEventListener("click", () => setTimeout(loadFeesPackages, 0));
    });

    if (!document.getElementById("activation-fee-panel")?.hidden) loadFeesPackages();
})();
