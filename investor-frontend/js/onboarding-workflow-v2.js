(() => {
    "use strict";

    const COPIER_DOWNLOAD_URL = "https://github.com/BethelTradingTech/Bethel/releases/download/copier-v1.0.1/BethelCopierSetup.exe";
    const COPIER_DOWNLOAD_KEY = "bethel_copier_downloaded_v1_0_1";
    const PRODUCTION_API_ORIGIN = "https://api.betheltradingtechnologies.com";
    const LEGACY_API_ORIGIN = "https://bethel-api.onrender.com";

    // Normalize all browser API traffic to Bethel's canonical production API.
    const nativeFetch = window.fetch.bind(window);
    window.fetch = async (input, init) => {
        const originalUrl = typeof input === "string" ? input : input instanceof Request ? input.url : "";
        const isBethelApi = originalUrl.startsWith(PRODUCTION_API_ORIGIN) || originalUrl.startsWith(LEGACY_API_ORIGIN);
        if (!isBethelApi) return nativeFetch(input, init);

        const path = originalUrl.startsWith(PRODUCTION_API_ORIGIN)
            ? originalUrl.slice(PRODUCTION_API_ORIGIN.length)
            : originalUrl.slice(LEGACY_API_ORIGIN.length);
        const canonicalUrl = PRODUCTION_API_ORIGIN + path;
        const fallbackUrl = LEGACY_API_ORIGIN + path;
        const buildInput = url => input instanceof Request ? new Request(url, input) : url;
        try {
            return await nativeFetch(buildInput(canonicalUrl), init);
        } catch (error) {
            if (!(error instanceof TypeError)) throw error;
            return nativeFetch(buildInput(fallbackUrl), init);
        }
    };

    // Legal documents must actually load before a subscriber can accept them.
    // onboarding.js starts before this compatibility layer, so retry the legal
    // request after canonical API routing has been installed.
    const legalButton = document.getElementById("accept-legal-documents");
    const legalCheckbox = document.getElementById("legal-consent-checkbox");
    if (legalButton) legalButton.disabled = true;
    if (legalCheckbox) legalCheckbox.disabled = true;

    async function repairLegalDocumentLoading() {
        if (!subscriberToken() || !subscriberId() || typeof loadLegalDocuments !== "function") return;
        const container = document.getElementById("legal-documents");
        try {
            if (container) container.textContent = "Loading current legal documents…";
            await loadLegalDocuments();
            const loadedDocuments = document.querySelectorAll("#legal-documents .legal-document");
            if (!loadedDocuments.length) throw new Error("No current legal documents were returned by the server.");
            if (legalCheckbox && !legalCheckbox.checked) legalCheckbox.disabled = false;
            if (legalButton && legalButton.textContent !== "Legal documents accepted") legalButton.disabled = false;
            setMessage("legal-consent-message", `Loaded ${loadedDocuments.length} current legal document${loadedDocuments.length === 1 ? "" : "s"}. Open and read each document before accepting.`, "success");
        } catch (error) {
            if (container) container.textContent = "Legal documents could not be loaded. Please retry or contact Bethel support.";
            if (legalCheckbox) { legalCheckbox.checked = false; legalCheckbox.disabled = true; }
            if (legalButton) legalButton.disabled = true;
            setMessage("legal-consent-message", error.message || "Unable to load legal documents.", "error");
        }
    }

    legalButton?.addEventListener("click", event => {
        if (!document.querySelector("#legal-documents .legal-document")) {
            event.preventDefault();
            event.stopImmediatePropagation();
            setMessage("legal-consent-message", "Legal documents must load before they can be accepted.", "error");
            repairLegalDocumentLoading();
        }
    }, true);

    const WORKFLOW_STEPS = [
        {step:3, displayStep:1, label:"Plan", description:"Select service plan", target:"registration-step-3"},
        {step:4, displayStep:2, label:"Identity", description:"Complete KYC verification", target:"registration-step-4"},
        {step:5, displayStep:3, label:"Broker", description:"Link your MT5 account", target:"registration-step-5"},
        {step:6, displayStep:4, label:"Legal", description:"Accept legal agreements", target:"legal-consent-panel"},
        {step:7, displayStep:5, label:"Fees", description:"Review activation fee", target:"profit-share-panel"},
        {step:8, displayStep:6, label:"Download", description:"Download Bethel Copier", target:"copier-download-panel"},
        {step:9, displayStep:7, label:"Activate", description:"Activate Bethel Copier", target:"copier-activation-panel"},
        {step:10, displayStep:8, label:"Payment", description:"Complete subscription payment", target:"registration-step-10"},
        {step:11, displayStep:9, label:"Approval", description:"Final Super Admin approval", target:"registration-step-11"},
        {step:12, displayStep:10, label:"Active", description:"Open active dashboard", target:"registration-step-11"}
    ];

    const statusIs = (value, accepted) => accepted.includes(String(value || "").toUpperCase());
    const getStatus = (source, names, fallback = "PENDING") => {
        for (const name of names) {
            if (source && source[name] !== undefined && source[name] !== null) return String(source[name]).toUpperCase();
        }
        return fallback;
    };

    window.markProgressStep = function(step) {
        const definition = WORKFLOW_STEPS.find(item => item.step === Number(step));
        const visibleStep = definition?.displayStep || 1;
        document.querySelectorAll(".progress-item").forEach((item, index) => {
            const active = index + 1 === visibleStep;
            item.classList.toggle("current", active);
            item.setAttribute("aria-current", active ? "step" : "false");
        });
    };

    window.openRegistrationStep = function(step, scroll = true) {
        const requested = Math.min(12, Math.max(3, Number(step) || 3));
        const definition = WORKFLOW_STEPS.find(item => item.step === requested);
        if (!definition?.target || !subscriberToken()) return;
        document.querySelectorAll(".registration-step-panel").forEach(panel => panel.hidden = true);
        const panel = document.getElementById(definition.target);
        if (!panel) return;
        panel.hidden = false;
        panel.dataset.visibleRegistrationStep = String(definition.displayStep);
        sessionStorage.setItem("bethel_registration_step", String(requested));
        window.markProgressStep(requested);
        if (requested === 6) repairLegalDocumentLoading();
        const reviewTitle = document.getElementById("review-activation-title");
        const reviewKicker = document.getElementById("review-activation-kicker");
        const reviewDescription = document.getElementById("review-activation-description");
        if (reviewTitle && reviewKicker && reviewDescription && definition.target === "registration-step-11") {
            if (requested === 12) {
                reviewKicker.textContent = "Step 10 of 10";
                reviewTitle.textContent = "Active dashboard";
                reviewDescription.textContent = "Your dashboard is available after all requirements and final Super Admin approval are complete.";
            } else {
                reviewKicker.textContent = "Step 9 of 10";
                reviewTitle.textContent = "Final Super Admin approval";
                reviewDescription.textContent = "Payment is complete. Bethel performs the final activation review before dashboard access is enabled.";
            }
        }
        document.querySelectorAll(".registration-step-button").forEach(button => {
            const active = Number(button.dataset.step) === requested;
            button.classList.toggle("active", active);
            button.setAttribute("aria-current", active ? "step" : "false");
        });
        closeRegistrationSettings();
        if (scroll) panel.scrollIntoView({behavior:"smooth", block:"start"});
    };

    window.initializeRegistrationNavigation = function() {
        const menu = document.getElementById("registration-step-menu");
        if (!menu) return;
        menu.replaceChildren();
        if (!subscriberToken()) {
            createNavigationButton(menu, {number:"⌂", label:"Home", description:"Return to the public website", onClick:() => {window.location.href = "https://betheltradingtechnologies.com/";}});
            createNavigationButton(menu, {number:"1", label:"Register", description:"Create a new Bethel account", active:!document.getElementById("registration-panel").hidden, onClick:showRegistration});
            createNavigationButton(menu, {number:"→", label:"Subscriber login", description:"Access an existing account", active:!document.getElementById("login-panel").hidden, onClick:showLogin});
            return;
        }
        WORKFLOW_STEPS.forEach(item => {
            const button = createNavigationButton(menu, {number:String(item.displayStep), label:item.label, description:item.description, onClick:() => window.openRegistrationStep(item.step)});
            button.dataset.step = String(item.step);
        });
        document.querySelectorAll(".progress-item").forEach((item, index) => {
            const definition = WORKFLOW_STEPS[index];
            if (!definition) return;
            item.tabIndex = 0;
            item.setAttribute("role", "button");
            item.onclick = () => window.openRegistrationStep(definition.step);
            item.onkeydown = event => {
                if (event.key === "Enter" || event.key === " ") { event.preventDefault(); window.openRegistrationStep(definition.step); }
            };
        });
    };

    window.updateRegistrationStepStates = function(source = {}) {
        const activation = getStatus(source, ["activation_status", "copy_trading_status", "status"]);
        const copier = getStatus(source, ["copier_status", "receiver_status", "copy_status", "copy_trading_status", "activation_status"]);
        const complete = {
            3: statusIs(getStatus(source, ["subscription_status", "subscription", "subscription_state"]), ["ACTIVE", "APPROVED", "COMPLETE", "PENDING_PAYMENT", "PAID"]),
            4: statusIs(getStatus(source, ["kyc_status", "kyc", "identity_status"]), ["APPROVED", "COMPLETE", "VERIFIED"]),
            5: statusIs(getStatus(source, ["broker_status", "mt5_status", "broker", "mt5"]), ["CONNECTED", "COMPLETE", "APPROVED", "VERIFIED"]),
            8: localStorage.getItem(COPIER_DOWNLOAD_KEY) === "true",
            9: statusIs(copier, ["CONNECTED", "READY", "ACTIVE", "ACTIVATED", "COMPLETE", "APPROVED"]),
            10: statusIs(getStatus(source, ["payment_status", "payment", "billing_status"]), ["PAID", "COMPLETE", "APPROVED"]),
            11: statusIs(getStatus(source, ["admin_status", "admin_approval", "approval_status"]), ["APPROVED", "COMPLETE", "ACTIVE"]),
            12: statusIs(activation, ["ACTIVE", "ACTIVATED", "COMPLETE", "APPROVED"])
        };
        document.querySelectorAll(".registration-step-button").forEach(button => button.classList.toggle("complete", Boolean(complete[Number(button.dataset.step)])));
        document.querySelectorAll(".progress-item").forEach((item, index) => {
            const definition = WORKFLOW_STEPS[index];
            item.classList.toggle("complete", Boolean(definition && complete[definition.step]));
        });
        const copierStatus = document.getElementById("copier-activation-status");
        if (copierStatus) copierStatus.textContent = complete[9] ? "CONNECTED" : copier;
    };

    const downloadLink = document.getElementById("bethel-copier-download");
    if (downloadLink) {
        downloadLink.href = COPIER_DOWNLOAD_URL;
        downloadLink.addEventListener("click", () => {
            localStorage.setItem(COPIER_DOWNLOAD_KEY, "true");
            setMessage("copier-download-message", "Bethel Copier download started. Install it, then continue to Step 7.", "success");
            window.initializeRegistrationNavigation();
        });
    }
    document.getElementById("copier-continue-activation")?.addEventListener("click", () => window.openRegistrationStep(9));
    document.getElementById("copier-refresh-status")?.addEventListener("click", refreshStatus);
    document.getElementById("copier-continue-payment")?.addEventListener("click", () => window.openRegistrationStep(10));

    const nativeKycScript = document.createElement("script");
    nativeKycScript.src = "js/native-kyc.js?v=1";
    nativeKycScript.defer = true;
    document.head.appendChild(nativeKycScript);

    const storedStep = Number(sessionStorage.getItem("bethel_registration_step") || 3);
    const safeStep = storedStep > 10 ? storedStep : (storedStep === 8 ? 10 : storedStep === 9 ? 11 : storedStep);
    if (subscriberToken() && subscriberId()) {
        window.initializeRegistrationNavigation();
        window.openRegistrationStep(safeStep, false);
        repairLegalDocumentLoading();
    }
})();
