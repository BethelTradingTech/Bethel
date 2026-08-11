(() => {
    "use strict";

    const base = () => typeof ONBOARDING_API !== "undefined" ? ONBOARDING_API : "https://bethel-api.onrender.com";
    const sid = () => Number(localStorage.getItem("bethel_subscriber_id") || 0);
    const token = () => localStorage.getItem("bethel_subscriber_access_token") || "";
    const authHeaders = () => ({"Accept":"application/json","Authorization":`Bearer ${token()}`});

    async function jsonRequest(path, options={}) {
        const response = await fetch(base()+path, options);
        let data={};
        try { data=await response.json(); } catch (_) {}
        if(!response.ok){
            const detail=data.detail;
            const message=typeof detail === "string" ? detail : detail?.message || data.message || `Request failed (${response.status})`;
            throw new Error(message);
        }
        return data;
    }

    function setNativeMessage(message, type="") {
        const el=document.getElementById("kyc-message");
        if(!el)return;
        el.textContent=message||"";
        el.className=`form-message ${type}`.trim();
    }

    function buildForm(session) {
        const panel=document.getElementById("registration-step-4");
        if(!panel)return;
        document.getElementById("sumsub-websdk-container")?.remove();
        document.getElementById("bethel-native-kyc-form")?.remove();
        const form=document.createElement("form");
        form.id="bethel-native-kyc-form";
        form.enctype="multipart/form-data";
        form.innerHTML=`
            <div class="account-safety">
                <strong>Bethel Native Identity Verification</strong>
                <p>Your identity evidence is encrypted and processed through Bethel's native verification pipeline. PEP and adverse-media review remain separate compliance follow-up items.</p>
            </div>
            <label for="native-date-of-birth">Date of birth</label>
            <input id="native-date-of-birth" type="date" required>
            <label for="native-nationality">Nationality (3-letter code)</label>
            <input id="native-nationality" type="text" minlength="3" maxlength="3" placeholder="GHA" required>
            <label for="native-document-type">Identity document</label>
            <select id="native-document-type" required>
                <option value="passport">Passport</option>
                <option value="national_id">National ID card</option>
                <option value="drivers_licence">Driver's licence</option>
                <option value="residence_permit">Residence permit</option>
            </select>
            <label for="native-issuing-country">Issuing country (3-letter code)</label>
            <input id="native-issuing-country" type="text" minlength="3" maxlength="3" placeholder="GHA" required>
            <label for="native-document-number">Document number</label>
            <input id="native-document-number" type="text" autocomplete="off" required>
            <label for="native-document-expiry">Document expiry date</label>
            <input id="native-document-expiry" type="date" required>
            <label for="native-document-front">Document front / passport photo page</label>
            <input id="native-document-front" type="file" accept="image/jpeg,image/png,image/webp,application/pdf" required>
            <label for="native-document-back">Document back (required for ID cards/licences)</label>
            <input id="native-document-back" type="file" accept="image/jpeg,image/png,image/webp,application/pdf">
            <label for="native-selfie">Live selfie</label>
            <input id="native-selfie" type="file" accept="image/jpeg,image/png,image/webp" capture="user" required>
            <label class="consent-check"><input id="native-kyc-consent" type="checkbox" required> I confirm this is my identity document and live selfie and consent to Bethel's identity and sanctions checks.</label>
            <button id="native-kyc-submit" type="submit">Submit secure verification</button>
        `;
        panel.appendChild(form);
        form.addEventListener("submit", event => submitForm(event, session));
    }

    async function submitForm(event, session) {
        event.preventDefault();
        const button=document.getElementById("native-kyc-submit");
        if(button){button.disabled=true;button.textContent="Verifying securely...";}
        setNativeMessage("Encrypting evidence and running Bethel identity checks...");
        try{
            const docType=document.getElementById("native-document-type").value;
            const back=document.getElementById("native-document-back").files[0];
            if(["national_id","drivers_licence"].includes(docType) && !back){
                throw new Error("The back of this document is required.");
            }
            const body=new FormData();
            body.append("reference",session.reference);
            body.append("challenge",session.challenge);
            body.append("date_of_birth",document.getElementById("native-date-of-birth").value);
            body.append("nationality",document.getElementById("native-nationality").value.trim().toUpperCase());
            body.append("document_type",docType);
            body.append("issuing_country",document.getElementById("native-issuing-country").value.trim().toUpperCase());
            body.append("document_number",document.getElementById("native-document-number").value.trim());
            body.append("document_expiry",document.getElementById("native-document-expiry").value);
            body.append("document_front",document.getElementById("native-document-front").files[0]);
            if(back)body.append("document_back",back);
            body.append("selfie",document.getElementById("native-selfie").files[0]);
            const result=await jsonRequest(`/kyc/${sid()}/native/submit`,{method:"POST",headers:authHeaders(),body});
            if(result.kyc_status === "APPROVED"){
                setNativeMessage("Identity verified successfully by Bethel Native KYC. You may continue to the broker-linking step.","success");
                form.remove();
                if(typeof refreshStatus === "function")await refreshStatus();
                setTimeout(()=>typeof openRegistrationStep === "function" && openRegistrationStep(5),900);
            }else if(result.kyc_status === "REJECTED"){
                setNativeMessage("Identity verification could not be approved. Contact Bethel Compliance for review.","error");
            }else{
                setNativeMessage("Identity evidence was received securely and requires Compliance review.","success");
            }
        }catch(error){
            setNativeMessage(error.message,"error");
        }finally{
            if(button){button.disabled=false;button.textContent="Submit secure verification";}
        }
    }

    async function startNativeKyc() {
        if(!sid() || !token()){
            setNativeMessage("Sign in before starting identity verification.","error");
            return;
        }
        const button=document.getElementById("kyc-submit-button");
        if(button){button.disabled=true;button.textContent="Preparing secure verification...";}
        try{
            const readiness=await jsonRequest("/kyc/native/readiness",{headers:authHeaders()});
            if(!readiness.ready_for_native_identity)throw new Error("Bethel Native KYC is temporarily unavailable. Please try again shortly.");
            const session=await jsonRequest(`/kyc/${sid()}/native/session`,{method:"POST",headers:authHeaders()});
            buildForm(session);
            setNativeMessage("Secure verification session created. Complete the fields below.","success");
        }catch(error){
            setNativeMessage(error.message,"error");
        }finally{
            if(button){button.disabled=false;button.textContent="Start Bethel Native KYC";}
        }
    }

    function activate() {
        const old=document.getElementById("kyc-submit-button");
        if(!old || old.dataset.nativeKycBound === "true")return;
        const replacement=old.cloneNode(true);
        replacement.dataset.nativeKycBound="true";
        replacement.textContent="Start Bethel Native KYC";
        old.replaceWith(replacement);
        replacement.addEventListener("click",startNativeKyc);
        document.getElementById("sumsub-websdk-container")?.remove();
    }

    if(document.readyState === "loading")document.addEventListener("DOMContentLoaded",activate);
    else activate();
})();
