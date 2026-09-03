(() => {
    "use strict";

    const base = () => typeof ONBOARDING_API !== "undefined" ? ONBOARDING_API : "https://bethel-api.onrender.com";
    const sid = () => Number(localStorage.getItem("bethel_subscriber_id") || 0);
    const token = () => localStorage.getItem("bethel_subscriber_access_token") || "";
    const authHeaders = () => ({"Accept":"application/json","Authorization":`Bearer ${token()}`});
    let handoffPoller = null;

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

    function handoffPageUrl(handoffToken) {
        const url=new URL("kyc-handoff.html", window.location.href);
        url.search="";
        url.hash=new URLSearchParams({token:handoffToken}).toString();
        return url.toString();
    }

    async function ensureQrLibrary() {
        if(window.QRCode)return true;
        return new Promise(resolve=>{
            const existing=document.querySelector('script[data-bethel-qr="true"]');
            if(existing){
                existing.addEventListener("load",()=>resolve(Boolean(window.QRCode)),{once:true});
                existing.addEventListener("error",()=>resolve(false),{once:true});
                return;
            }
            const script=document.createElement("script");
            script.src="https://cdn.jsdelivr.net/npm/qrcode@1.5.4/build/qrcode.min.js";
            script.defer=true;
            script.dataset.bethelQr="true";
            script.onload=()=>resolve(Boolean(window.QRCode));
            script.onerror=()=>resolve(false);
            document.head.appendChild(script);
        });
    }

    function stopHandoffPolling() {
        if(handoffPoller){clearInterval(handoffPoller);handoffPoller=null;}
    }

    async function attachRemoteSelfie(session) {
        const response=await fetch(base()+`/kyc/${sid()}/native/handoff/selfie?reference=${encodeURIComponent(session.reference)}`,{headers:authHeaders(),cache:"no-store"});
        if(!response.ok)throw new Error("The selfie was captured but could not be transferred back to this device.");
        const blob=await response.blob();
        const contentType=blob.type||"image/jpeg";
        const extension=contentType.includes("png")?"png":contentType.includes("webp")?"webp":"jpg";
        const file=new File([blob],`live-selfie.${extension}`,{type:contentType,lastModified:Date.now()});
        const input=document.getElementById("native-selfie");
        if(!input)throw new Error("Live selfie field is unavailable.");
        const transfer=new DataTransfer();
        transfer.items.add(file);
        input.files=transfer.files;
        input.dataset.remoteCapture="true";
        const box=document.getElementById("native-device-handoff");
        if(box)box.innerHTML='<div class="account-safety"><strong>Selfie received from your other device</strong><p>The secure handoff is complete. Review the remaining fields and submit your verification on this device.</p></div>';
        setNativeMessage("Live selfie received securely from your other device. You can now submit identity verification.","success");
        stopHandoffPolling();
    }

    async function pollHandoff(session) {
        try{
            const result=await jsonRequest(`/kyc/${sid()}/native/handoff/status?reference=${encodeURIComponent(session.reference)}`,{headers:authHeaders(),cache:"no-store"});
            if(result.captured)await attachRemoteSelfie(session);
        }catch(error){
            stopHandoffPolling();
            setNativeMessage(error.message,"error");
        }
    }

    async function startDeviceHandoff(session) {
        const button=document.getElementById("native-handoff-button");
        if(button){button.disabled=true;button.textContent="Creating secure handoff...";}
        try{
            const result=await jsonRequest(`/kyc/${sid()}/native/handoff`,{
                method:"POST",
                headers:{...authHeaders(),"Content-Type":"application/json"},
                body:JSON.stringify({reference:session.reference,challenge:session.challenge})
            });
            if(result.status==="captured"){
                await attachRemoteSelfie(session);
                return;
            }
            if(!result.handoff_token)throw new Error("Secure handoff token was not created.");
            const url=handoffPageUrl(result.handoff_token);
            const box=document.getElementById("native-device-handoff");
            if(!box)return;
            box.hidden=false;
            box.innerHTML=`
                <div class="account-safety">
                    <strong>Continue your live selfie on another device</strong>
                    <p>Scan the QR code with your phone or copy the secure link. The link expires in about ${Math.max(1,Math.round(Number(result.expires_in||600)/60))} minutes and only permits this selfie capture.</p>
                    <canvas id="native-handoff-qr" width="220" height="220" aria-label="Secure KYC handoff QR code"></canvas>
                    <input id="native-handoff-url" type="text" readonly value="${url.replace(/&/g,"&amp;").replace(/"/g,"&quot;")}">
                    <button id="native-handoff-copy" type="button" class="secondary-button">Copy secure link</button>
                    <button id="native-handoff-share" type="button" class="secondary-button">Share to my phone</button>
                    <p id="native-handoff-status" class="form-message">Waiting for the other device...</p>
                </div>`;
            document.getElementById("native-handoff-copy")?.addEventListener("click",async()=>{
                await navigator.clipboard.writeText(url);
                const status=document.getElementById("native-handoff-status");
                if(status)status.textContent="Secure link copied.";
            });
            const shareButton=document.getElementById("native-handoff-share");
            if(shareButton){
                if(navigator.share)shareButton.addEventListener("click",()=>navigator.share({title:"Bethel identity verification",text:"Continue my Bethel live selfie",url}).catch(()=>{}));
                else shareButton.hidden=true;
            }
            if(await ensureQrLibrary()){
                try{await window.QRCode.toCanvas(document.getElementById("native-handoff-qr"),url,{width:220,margin:1});}catch(_){}
            }
            stopHandoffPolling();
            await pollHandoff(session);
            handoffPoller=setInterval(()=>pollHandoff(session),2500);
        }catch(error){
            setNativeMessage(error.message,"error");
        }finally{
            if(button){button.disabled=false;button.textContent="Continue selfie on another device";}
        }
    }

    function buildForm(session) {
        const panel=document.getElementById("registration-step-4");
        if(!panel)return;
        stopHandoffPolling();
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
            <button id="native-handoff-button" type="button" class="secondary-button">Continue selfie on another device</button>
            <div id="native-device-handoff" hidden></div>
            <p class="muted">If this device has no camera or the camera quality is poor, use the secure handoff above. Your other device receives access only to this live-selfie capture, not your Bethel account.</p>
            <label class="consent-check"><input id="native-kyc-consent" type="checkbox" required> I confirm this is my identity document and live selfie and consent to Bethel's identity and sanctions checks.</label>
            <button id="native-kyc-submit" type="submit">Submit secure verification</button>
        `;
        panel.appendChild(form);
        document.getElementById("native-handoff-button")?.addEventListener("click",()=>startDeviceHandoff(session));
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
            const selfie=document.getElementById("native-selfie").files[0];
            if(!selfie)throw new Error("Take a live selfie on this device or continue the selfie on another device.");
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
            body.append("selfie",selfie);
            const result=await jsonRequest(`/kyc/${sid()}/native/submit`,{method:"POST",headers:authHeaders(),body});
            stopHandoffPolling();
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
            if(!readiness.available && !readiness.ready_for_native_identity)throw new Error("Bethel Native KYC is temporarily unavailable. Please try again shortly.");
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

    window.addEventListener("pagehide",stopHandoffPolling);
    if(document.readyState === "loading")document.addEventListener("DOMContentLoaded",activate);
    else activate();
})();
