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
});
