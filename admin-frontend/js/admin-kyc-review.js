(() => {
  const API_BASE = (location.hostname === "localhost" || location.hostname === "127.0.0.1")
    ? "http://127.0.0.1:8000"
    : (location.hostname === "bethel-api.onrender.com" || location.hostname === "api.betheltradingtechnologies.com")
      ? location.origin
      : "https://bethel-api.onrender.com";

  const state = { objectUrls: [] };
  const esc = value => String(value ?? "").replace(/[&<>"']/g, ch => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  }[ch]));

  function token() {
    return localStorage.getItem("bethel_access_token");
  }

  async function reviewRequest(path, options = {}) {
    const headers = { Accept: "application/json", ...(options.headers || {}) };
    const accessToken = token();
    if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
    if (options.body && !headers["Content-Type"]) headers["Content-Type"] = "application/json";
    const response = await fetch(API_BASE + path, { credentials: "include", ...options, headers });
    const type = response.headers.get("content-type") || "";
    const data = type.includes("application/json") ? await response.json() : await response.text();
    if (!response.ok) {
      const detail = data && typeof data === "object" ? data.detail : data;
      throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail || `API error ${response.status}`));
    }
    return data;
  }

  function ensureStyles() {
    if (document.getElementById("native-kyc-review-styles")) return;
    const style = document.createElement("style");
    style.id = "native-kyc-review-styles";
    style.textContent = `
      .kyc-review-button{background:#0ea5e9!important;color:#fff!important;border-color:#38bdf8!important;font-weight:700}
      .kyc-direct-disabled{opacity:.42!important;pointer-events:none!important}
      .kyc-modal-backdrop{position:fixed;inset:0;background:rgba(2,6,23,.86);z-index:10000;display:flex;align-items:flex-start;justify-content:center;padding:3vh 18px;overflow:auto}
      .kyc-modal{width:min(1120px,100%);background:#071426;border:1px solid #1e3a5f;border-radius:18px;box-shadow:0 30px 100px rgba(0,0,0,.55);color:#e5eefb;overflow:hidden}
      .kyc-modal header{position:sticky;top:0;z-index:2;background:#071426f2;backdrop-filter:blur(12px);display:flex;justify-content:space-between;gap:20px;align-items:center;padding:20px 24px;border-bottom:1px solid #1e3a5f}
      .kyc-modal h2,.kyc-modal h3{margin:0}.kyc-modal main{padding:22px 24px 28px}.kyc-close{background:#172554!important;color:#fff!important;border:1px solid #334155!important}
      .kyc-warning{padding:14px 16px;border:1px solid #854d0e;background:#422006;color:#fde68a;border-radius:12px;margin-bottom:18px;font-weight:600}
      .kyc-review-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:12px;margin:14px 0 22px}
      .kyc-review-card{background:#0b1d33;border:1px solid #1e3a5f;border-radius:12px;padding:13px}.kyc-review-card small{display:block;color:#93a4b8;margin-bottom:5px}.kyc-review-card strong{overflow-wrap:anywhere}
      .kyc-checks{width:100%;border-collapse:collapse;margin-top:10px}.kyc-checks th,.kyc-checks td{text-align:left;padding:10px;border-bottom:1px solid #1e3a5f;vertical-align:top}.kyc-checks small{color:#94a3b8}
      .kyc-check-passed{color:#34d399}.kyc-check-failed{color:#fb7185}.kyc-check-review,.kyc-check-not_available{color:#fbbf24}
      .kyc-evidence-toolbar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:16px 0}.kyc-evidence-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
      .kyc-evidence-item{background:#0b1d33;border:1px solid #1e3a5f;border-radius:12px;padding:12px}.kyc-evidence-item img,.kyc-evidence-item iframe{width:100%;height:360px;object-fit:contain;background:#020617;border:0;border-radius:8px}
      .kyc-decision{margin-top:24px;padding-top:20px;border-top:1px solid #1e3a5f}.kyc-decision textarea{width:100%;min-height:90px;background:#020617;color:#e5eefb;border:1px solid #334155;border-radius:10px;padding:10px;margin:10px 0 14px}
      .kyc-attest{display:flex;gap:10px;align-items:flex-start;margin:14px 0}.kyc-attest input{margin-top:4px}.kyc-actions{display:flex;gap:12px;flex-wrap:wrap}.kyc-approve{background:#059669!important;color:#fff!important}.kyc-reject{background:#b91c1c!important;color:#fff!important}.kyc-actions button:disabled{opacity:.45;cursor:not-allowed}
      .kyc-spinner{padding:40px;text-align:center;color:#93c5fd}.kyc-error{padding:16px;border-radius:10px;background:#450a0a;color:#fecaca;border:1px solid #991b1b}
    `;
    document.head.appendChild(style);
  }

  function clearObjectUrls() {
    state.objectUrls.forEach(url => URL.revokeObjectURL(url));
    state.objectUrls = [];
  }

  function closeModal() {
    clearObjectUrls();
    document.getElementById("native-kyc-review-modal")?.remove();
  }

  function field(label, value) {
    return `<div class="kyc-review-card"><small>${esc(label)}</small><strong>${esc(value || "—")}</strong></div>`;
  }

  function checksTable(checks) {
    const entries = Object.entries(checks || {});
    if (!entries.length) return '<p class="kyc-warning">No automated check results were recorded for this session.</p>';
    return `<table class="kyc-checks"><thead><tr><th>Check</th><th>Status</th><th>Score</th><th>Reasons</th></tr></thead><tbody>${entries.map(([name, row]) => {
      const status = String(row.status || "unknown");
      return `<tr><td><strong>${esc(name.replaceAll("_", " "))}</strong><br><small>${esc(row.engine_version || "")}</small></td><td class="kyc-check-${esc(status)}">${esc(status.toUpperCase())}</td><td>${row.score ?? "—"}</td><td>${(row.reasons || []).map(esc).join("<br>") || "—"}</td></tr>`;
    }).join("")}</tbody></table>`;
  }

  async function loadEvidence(subscriberId, evidenceRows, target, button) {
    button.disabled = true;
    button.textContent = "Loading protected evidence…";
    target.innerHTML = "";
    try {
      for (const row of evidenceRows || []) {
        const headers = {};
        const accessToken = token();
        if (accessToken) headers.Authorization = `Bearer ${accessToken}`;
        const response = await fetch(API_BASE + row.review_url, { credentials: "include", headers, cache: "no-store" });
        if (!response.ok) throw new Error(`Unable to load ${row.category} (${response.status})`);
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        state.objectUrls.push(url);
        const media = String(row.content_type || "").startsWith("image/")
          ? `<img src="${url}" alt="${esc(row.category)} KYC evidence">`
          : row.content_type === "application/pdf"
            ? `<iframe src="${url}" title="${esc(row.category)} KYC evidence"></iframe>`
            : `<p>Evidence loaded. Preview is unavailable for ${esc(row.content_type)}.</p>`;
        target.insertAdjacentHTML("beforeend", `<div class="kyc-evidence-item"><strong>${esc(row.category.replaceAll("-", " "))}</strong><br><small>${esc(row.content_type)} · ${Number(row.size_bytes || 0).toLocaleString()} bytes · SHA-256 ${esc(row.sha256_prefix)}…</small>${media}</div>`);
      }
      if (!(evidenceRows || []).length) target.innerHTML = '<p class="kyc-error">No identity evidence is registered for this KYC session.</p>';
      button.textContent = "Evidence revealed for this review";
    } catch (error) {
      target.innerHTML = `<p class="kyc-error">${esc(error.message || "Unable to load protected evidence")}</p>`;
      button.disabled = false;
      button.textContent = "Retry protected evidence";
    }
  }

  async function submitDecision(subscriberId, decision, reason, attestation, button) {
    if (decision === "REJECTED" && String(reason || "").trim().length < 3) {
      alert("Enter a clear rejection reason before rejecting KYC.");
      return;
    }
    const verb = decision === "APPROVED" ? "APPROVE" : "REJECT";
    if (!confirm(`${verb} this Native KYC submission after reviewing the evidence and checks?`)) return;
    button.disabled = true;
    try {
      await reviewRequest(`/admin/kyc/native/${subscriberId}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision, reason: String(reason || "").trim() || null, attestation: !!attestation })
      });
      closeModal();
      if (typeof setStatus === "function") setStatus(`Native KYC ${decision.toLowerCase()} after Compliance review`);
      if (typeof loadOverview === "function") await loadOverview();
    } catch (error) {
      alert(error.message || "KYC decision failed");
      button.disabled = false;
    }
  }

  async function openReview(subscriberId) {
    ensureStyles();
    closeModal();
    const backdrop = document.createElement("div");
    backdrop.id = "native-kyc-review-modal";
    backdrop.className = "kyc-modal-backdrop";
    backdrop.innerHTML = '<section class="kyc-modal"><header><div><h2>Native KYC Compliance Review</h2><small>Loading protected review record…</small></div><button class="kyc-close" type="button">Close</button></header><main><div class="kyc-spinner">Loading KYC session, checks and evidence manifest…</div></main></section>';
    document.body.appendChild(backdrop);
    backdrop.querySelector(".kyc-close").onclick = closeModal;
    backdrop.addEventListener("click", event => { if (event.target === backdrop) closeModal(); });

    try {
      const data = await reviewRequest(`/admin/kyc/native/${subscriberId}`);
      const session = data.session || {}, identity = data.identity || {}, risk = data.risk || {}, subscriber = data.subscriber || {};
      backdrop.querySelector("header small").textContent = `${subscriber.name || "Subscriber"} · ID ${subscriber.id || subscriberId} · ${session.reference || ""}`;
      const main = backdrop.querySelector("main");
      main.innerHTML = `
        <div class="kyc-warning">Sensitive identity data. Authorized Compliance/Admin review only. Do not download, copy, photograph, or share identity evidence unless your documented compliance process requires it.</div>
        <h3>Identity & session</h3>
        <div class="kyc-review-grid">
          ${field("Registered name", subscriber.name)}${field("Email", subscriber.email)}${field("Session status", session.status)}${field("Decision", session.decision)}
          ${field("Date of birth", identity.date_of_birth)}${field("Nationality", identity.nationality)}${field("Document type", identity.document_type)}${field("Issuing country", identity.issuing_country)}
          ${field("Document expiry", identity.document_expiry)}${field("Document number", identity.document_number)}${field("Sanctions status", risk.sanctions_status)}${field("AML follow-up", risk.aml_followup_required ? "Required" : "Not required")}
          ${field("Liveness score", risk.liveness_score)}${field("Face-match score", risk.face_match_score)}${field("Submitted", data.onboarding?.kyc_submitted_at)}${field("Review reason", session.review_reason)}
        </div>
        <h3>Verification checks</h3>${checksTable(data.checks)}
        <section class="kyc-evidence-toolbar"><button type="button" class="kyc-review-button" id="kyc-reveal-evidence">Reveal protected passport / ID and selfie</button><small>Evidence is decrypted only for this authenticated review request and is sent with no-store headers.</small></section>
        <div class="kyc-evidence-grid" id="kyc-evidence-grid"></div>
        <section class="kyc-decision">
          <h3>Compliance decision</h3>
          <label for="kyc-review-note">Reviewer note / rejection reason</label>
          <textarea id="kyc-review-note" maxlength="500" placeholder="Record the basis for this manual review. A reason is mandatory for rejection."></textarea>
          <label class="kyc-attest"><input id="kyc-review-attestation" type="checkbox"><span>I confirm that I reviewed the identity evidence and verification checks shown above. I understand that PEP/adverse-media follow-up remains separate where required.</span></label>
          <div class="kyc-actions"><button type="button" class="kyc-approve" id="kyc-approve-reviewed" disabled>Approve after review</button><button type="button" class="kyc-reject" id="kyc-reject-reviewed">Reject after review</button></div>
        </section>`;

      const reveal = main.querySelector("#kyc-reveal-evidence");
      reveal.onclick = () => loadEvidence(subscriberId, data.evidence || [], main.querySelector("#kyc-evidence-grid"), reveal);
      const attestation = main.querySelector("#kyc-review-attestation");
      const approve = main.querySelector("#kyc-approve-reviewed");
      const reject = main.querySelector("#kyc-reject-reviewed");
      attestation.onchange = () => { approve.disabled = !attestation.checked; };
      approve.onclick = () => submitDecision(subscriberId, "APPROVED", main.querySelector("#kyc-review-note").value, attestation.checked, approve);
      reject.onclick = () => submitDecision(subscriberId, "REJECTED", main.querySelector("#kyc-review-note").value, attestation.checked, reject);
    } catch (error) {
      backdrop.querySelector("main").innerHTML = `<p class="kyc-error">${esc(error.message || "Unable to load Native KYC review")}</p>`;
    }
  }

  function securePendingKycActions() {
    const table = document.querySelector("#subscribers-table");
    if (!table) return;
    table.querySelectorAll('button[data-action="kyc-approve"]').forEach(approve => {
      const id = approve.dataset.id;
      const reject = table.querySelector(`button[data-action="kyc-reject"][data-id="${CSS.escape(id)}"]`);
      if (approve.disabled) return;
      approve.classList.add("kyc-direct-disabled");
      approve.disabled = true;
      approve.title = "Use Review KYC to inspect protected evidence before approval";
      if (reject) {
        reject.classList.add("kyc-direct-disabled");
        reject.disabled = true;
        reject.title = "Use Review KYC to inspect protected evidence before rejection";
      }
      const actions = approve.parentElement;
      if (!actions || actions.querySelector(`[data-native-kyc-review="${CSS.escape(id)}"]`)) return;
      const review = document.createElement("button");
      review.type = "button";
      review.className = "kyc-review-button";
      review.dataset.nativeKycReview = id;
      review.textContent = "Review KYC";
      review.title = "Open the protected Native KYC compliance review";
      review.onclick = () => openReview(Number(id));
      actions.insertBefore(review, approve);
    });
  }

  function start() {
    ensureStyles();
    securePendingKycActions();
    const table = document.querySelector("#subscribers-table");
    if (table) new MutationObserver(securePendingKycActions).observe(table, { childList: true, subtree: true });
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
