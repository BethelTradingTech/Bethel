let deferredInstallPrompt = null;


function isIos(){
    return /iphone|ipad|ipod/i.test(navigator.userAgent);
}


function isStandalone(){
    return window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;
}


async function installBethelApp(){
    if(deferredInstallPrompt){
        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice;
        deferredInstallPrompt = null;
        document.getElementById("install-app-button")?.remove();
        return;
    }

    if(isIos()){
        alert("On iPhone or iPad: tap Share, then choose Add to Home Screen.");
    }
}


if("serviceWorker" in navigator){
    window.addEventListener(
        "load",
        () => navigator.serviceWorker.register("./sw.js?v=4").then(registration => registration.update())
    );
}


window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    deferredInstallPrompt = event;
    document.getElementById("install-app-button")?.removeAttribute("hidden");
});


if(isIos() && !isStandalone()){
    document.getElementById("install-app-button")?.removeAttribute("hidden");
}


document.getElementById("install-app-button")?.addEventListener(
    "click",
    installBethelApp
);


function verificationApiBase(){
    if(typeof ONBOARDING_API !== "undefined")return ONBOARDING_API;
    if(["localhost","127.0.0.1"].includes(window.location.hostname) || window.location.hostname.startsWith("192.168.")){
        return `${window.location.protocol}//${window.location.hostname}:8000`;
    }
    return "https://bethel-api.onrender.com";
}


function ensureResendVerificationButton(){
    const message=document.getElementById("subscriber-login-error");
    const emailInput=document.getElementById("subscriber-email");
    if(!message||!emailInput)return;
    const text=String(message.textContent||"");
    const needsVerification=/verify your email|verification email|check your email/i.test(text);
    let button=document.getElementById("resend-verification-button");
    if(!needsVerification){button?.remove();return;}
    if(button)return;
    button=document.createElement("button");
    button.id="resend-verification-button";
    button.type="button";
    button.className="secondary-button";
    button.textContent="Resend verification email";
    button.addEventListener("click",async()=>{
        const email=emailInput.value.trim().toLowerCase();
        if(!email){message.textContent="Enter your email address first.";return;}
        button.disabled=true;
        button.textContent="Sending...";
        try{
            const response=await fetch(`${verificationApiBase()}/copytrading/auth/resend-verification`,{
                method:"POST",
                headers:{"Accept":"application/json","Content-Type":"application/json"},
                body:JSON.stringify({email})
            });
            let data={};
            try{data=await response.json();}catch(_){}
            if(!response.ok)throw new Error(data.detail||data.message||"Unable to resend verification email");
            message.textContent=data.message||"A new verification email has been sent.";
            message.className="form-message success";
        }catch(error){
            message.textContent=error.message;
            message.className="form-message error";
        }finally{
            button.disabled=false;
            button.textContent="Resend verification email";
        }
    });
    message.insertAdjacentElement("afterend",button);
}


function improveRegistrationVerificationMessage(){
    const message=document.getElementById("subscriber-login-error");
    if(!message)return;
    const current=String(message.textContent||"");
    if(/Account created successfully\. Enter your password to sign in\./i.test(current)){
        message.textContent="Account created. Check your email and verify your address before signing in.";
        message.className="form-message success";
    }
    ensureResendVerificationButton();
}


function ensureSubscriptionContinueButton(){
    const message=document.getElementById("subscription-message");
    if(!message)return;
    const saved=/subscription saved/i.test(String(message.textContent||""));
    let button=document.getElementById("subscription-continue-button");
    if(!saved){
        button?.remove();
        return;
    }
    if(button)return;
    button=document.createElement("button");
    button.id="subscription-continue-button";
    button.type="button";
    button.className="primary-button";
    button.textContent="Continue to identity verification";
    button.addEventListener("click",()=>{
        if(typeof openRegistrationStep === "function"){
            openRegistrationStep(4);
        }else{
            const identityPanel=document.getElementById("registration-step-4");
            if(identityPanel){
                document.querySelectorAll(".registration-step-panel").forEach(panel=>panel.hidden=true);
                identityPanel.hidden=false;
                identityPanel.scrollIntoView({behavior:"smooth",block:"start"});
            }
        }
    });
    message.insertAdjacentElement("afterend",button);
}


function promoHeaders(){
    const token=localStorage.getItem("bethel_subscriber_access_token");
    return {
        "Accept":"application/json",
        "Content-Type":"application/json",
        "Authorization":`Bearer ${token||""}`
    };
}


async function promoRequest(path,body){
    const response=await fetch(`${verificationApiBase()}${path}`,{
        method:"POST",
        headers:promoHeaders(),
        body:JSON.stringify(body)
    });
    let data={};
    try{data=await response.json();}catch(_){}
    if(!response.ok)throw new Error(data.detail||data.message||`Promo request failed (${response.status})`);
    return data;
}


function formatPromoMoney(value,currency){
    return `${Number(value||0).toFixed(2)} ${String(currency||"USD").toUpperCase()}`;
}


function buildPromoPanel(idPrefix){
    const wrapper=document.createElement("section");
    wrapper.id=`${idPrefix}-promo-panel`;
    wrapper.className="account-safety";
    wrapper.innerHTML=`
        <strong>Promo or discount code</strong>
        <p>Enter a valid code before payment. Restricted codes work only for the subscriber email assigned by Bethel.</p>
        <label for="${idPrefix}-promo-code">Promo code</label>
        <input id="${idPrefix}-promo-code" type="text" maxlength="40" autocomplete="off" placeholder="Enter promo code">
        <div style="display:flex;gap:.75rem;flex-wrap:wrap;margin-top:.75rem">
            <button id="${idPrefix}-promo-check" type="button" class="secondary-button">Check discount</button>
            <button id="${idPrefix}-promo-apply" type="button">Apply code</button>
        </div>
        <p id="${idPrefix}-promo-message" class="form-message"></p>
        <div id="${idPrefix}-promo-summary" class="payment-instructions" hidden></div>
    `;
    return wrapper;
}


function syncPromoInputs(sourceId){
    const source=document.getElementById(sourceId);
    if(!source)return;
    ["plan-promo-code","payment-promo-code"].forEach(id=>{
        const input=document.getElementById(id);
        if(input&&input!==source)input.value=source.value;
    });
}


function renderPromoResult(prefix,data,applied=false){
    const summary=document.getElementById(`${prefix}-promo-summary`);
    const message=document.getElementById(`${prefix}-promo-message`);
    if(summary){
        summary.hidden=false;
        summary.textContent=`Original: ${formatPromoMoney(data.original_amount,data.currency)} | Discount: ${formatPromoMoney(data.discount_amount,data.currency)} | Amount due: ${formatPromoMoney(data.final_amount,data.currency)}`;
    }
    if(message){
        message.textContent=applied
            ? (data.payment_waived?"Promo applied. Your subscription payment has been fully waived.":"Promo applied. The discounted amount is now due.")
            : "Promo code is valid. Click Apply code to use it.";
        message.className="form-message success";
    }
}


function wirePromoPanel(prefix){
    const input=document.getElementById(`${prefix}-promo-code`);
    const check=document.getElementById(`${prefix}-promo-check`);
    const apply=document.getElementById(`${prefix}-promo-apply`);
    if(!input||!check||!apply)return;
    input.addEventListener("input",()=>syncPromoInputs(input.id));

    check.addEventListener("click",async()=>{
        const code=input.value.trim();
        const id=Number(localStorage.getItem("bethel_subscriber_id")||0);
        if(!code){setMessage(`${prefix}-promo-message`,"Enter a promo code first.","error");return;}
        if(!id){setMessage(`${prefix}-promo-message`,"Sign in before checking a promo code.","error");return;}
        check.disabled=true;setMessage(`${prefix}-promo-message`,"Checking promo code...");
        try{
            const data=await promoRequest(`/payments/promos/${id}/quote`,{code});
            renderPromoResult(prefix,data,false);
        }catch(error){setMessage(`${prefix}-promo-message`,error.message,"error");}
        finally{check.disabled=false;}
    });

    apply.addEventListener("click",async()=>{
        const code=input.value.trim();
        const id=Number(localStorage.getItem("bethel_subscriber_id")||0);
        if(!code){setMessage(`${prefix}-promo-message`,"Enter a promo code first.","error");return;}
        if(!id){setMessage(`${prefix}-promo-message`,"Sign in before applying a promo code.","error");return;}
        apply.disabled=true;setMessage(`${prefix}-promo-message`,"Applying promo code...");
        try{
            const data=await promoRequest(`/payments/promos/${id}/redeem`,{code});
            renderPromoResult(prefix,data,true);
            localStorage.setItem("bethel_applied_promo_code",String(data.promo_code||code).toUpperCase());
            localStorage.setItem("bethel_discounted_amount",String(data.final_amount??""));
            if(typeof refreshStatus==="function")await refreshStatus();
        }catch(error){setMessage(`${prefix}-promo-message`,error.message,"error");}
        finally{apply.disabled=false;}
    });
}


function ensurePromoCodeControls(){
    const planForm=document.getElementById("subscription-form");
    if(planForm&&!document.getElementById("plan-promo-panel")){
        const panel=buildPromoPanel("plan");
        planForm.insertAdjacentElement("afterend",panel);
        wirePromoPanel("plan");
    }

    const paymentForm=document.getElementById("payment-form");
    if(paymentForm&&!document.getElementById("payment-promo-panel")){
        const panel=buildPromoPanel("payment");
        paymentForm.insertAdjacentElement("afterbegin",panel);
        wirePromoPanel("payment");
    }

    const saved=localStorage.getItem("bethel_applied_promo_code");
    if(saved){
        ["plan-promo-code","payment-promo-code"].forEach(id=>{
            const input=document.getElementById(id);
            if(input&&!input.value)input.value=saved;
        });
    }
}


window.addEventListener("DOMContentLoaded",()=>{
    const loginMessage=document.getElementById("subscriber-login-error");
    if(loginMessage){
        improveRegistrationVerificationMessage();
        new MutationObserver(improveRegistrationVerificationMessage).observe(loginMessage,{
            childList:true,
            characterData:true,
            subtree:true
        });
    }

    const subscriptionMessage=document.getElementById("subscription-message");
    if(subscriptionMessage){
        ensureSubscriptionContinueButton();
        new MutationObserver(ensureSubscriptionContinueButton).observe(subscriptionMessage,{
            childList:true,
            characterData:true,
            subtree:true
        });
    }

    ensurePromoCodeControls();
});
