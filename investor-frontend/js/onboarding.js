const ONBOARDING_API =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.startsWith("192.168.")
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : window.location.hostname === "bethel-api.onrender.com" ||
          window.location.hostname === "api.betheltradingtechnologies.com"
            ? window.location.origin
            : "https://bethel-api.onrender.com";

const SUBSCRIBER_TOKEN_KEY = "bethel_subscriber_access_token";
const SUBSCRIBER_ID_KEY = "bethel_subscriber_id";
const SUBSCRIBER_NAME_KEY = "bethel_subscriber_name";

function subscriberToken(){return localStorage.getItem(SUBSCRIBER_TOKEN_KEY);}
function subscriberId(){return Number(localStorage.getItem(SUBSCRIBER_ID_KEY)||0);}
function subscriberHeaders(json=false){
    const headers={"Accept":"application/json","Authorization":`Bearer ${subscriberToken()}`};
    if(json) headers["Content-Type"]="application/json";
    return headers;
}
function clearSubscriberSession(){
    localStorage.removeItem(SUBSCRIBER_TOKEN_KEY);
    localStorage.removeItem(SUBSCRIBER_ID_KEY);
    localStorage.removeItem(SUBSCRIBER_NAME_KEY);
}
function saveSubscriberSession(data){
    localStorage.setItem(SUBSCRIBER_TOKEN_KEY,data.access_token);
    localStorage.setItem(SUBSCRIBER_ID_KEY,String(data.subscriber_id));
    localStorage.setItem(SUBSCRIBER_NAME_KEY,data.name||"Subscriber");
}
function setMessage(id,message,type=""){
    const el=document.getElementById(id);
    if(!el)return;
    el.textContent=message||"";
    el.className=`form-message ${type}`.trim();
}
async function parseResponse(response){
    let data={};
    try{data=await response.json();}catch(_){}
    if(response.status===401||response.status===403){
        clearSubscriberSession();showLogin();
        throw new Error(data.detail||"Your session has expired. Please sign in again.");
    }
    if(!response.ok)throw new Error(data.detail||data.message||`Request failed (${response.status})`);
    return data;
}
async function apiRequest(path,options={}){
    return parseResponse(await fetch(ONBOARDING_API+path,options));
}
function normalizeStatus(value,fallback="PENDING"){
    if(value===true)return"COMPLETE";
    if(value===false||value===null||value===undefined||value==="")return fallback;
    return String(value).toUpperCase();
}
function pick(data,names,fallback="PENDING"){
    for(const name of names){
        if(data&&data[name]!==undefined&&data[name]!==null)return normalizeStatus(data[name],fallback);
    }
    return fallback;
}
function showLogin(){
    document.getElementById("registration-panel").hidden=true;
    document.getElementById("login-panel").hidden=false;
    document.getElementById("workflow").hidden=true;
    document.getElementById("subscriber-logout").hidden=true;
    document.getElementById("registration-settings-button").hidden=false;
    document.getElementById("activation-progress").hidden=true;
    initializeRegistrationNavigation();
    closeRegistrationSettings();
}
function showWorkflow(){
    document.getElementById("registration-panel").hidden=true;
    document.getElementById("login-panel").hidden=true;
    document.getElementById("workflow").hidden=false;
    document.getElementById("subscriber-logout").hidden=false;
    document.getElementById("registration-settings-button").hidden=false;
    document.getElementById("activation-progress").hidden=false;
    document.getElementById("subscriber-id").textContent=subscriberId();
    document.getElementById("subscriber-name").textContent=localStorage.getItem(SUBSCRIBER_NAME_KEY)||"Subscriber";
    initializeRegistrationNavigation();
    openRegistrationStep(Number(sessionStorage.getItem("bethel_registration_step")||3),false);
}
async function loadPlans(){
    const select=document.getElementById("plan-select");
    select.innerHTML='<option value="">Loading plans...</option>';
    try{
        const data=await apiRequest("/onboarding/plans",{headers:subscriberHeaders()});
        const plans=Array.isArray(data)?data:(data.plans||data.subscription_plans||data.data||[]);
        select.innerHTML='<option value="">Select a plan</option>';
        for(const plan of plans){
            const option=document.createElement("option");
            option.value=plan.id??plan.plan_id;
            const price=plan.price??plan.monthly_price??plan.amount;
            const priceText=price!==undefined&&price!==null?` Ã¢â‚¬â€ $${Number(price).toLocaleString("en-US")}`:"";
            option.textContent=`${plan.name||plan.plan_name||`Plan ${option.value}`}${priceText}`;
            select.appendChild(option);
        }
        if(!plans.length)select.innerHTML='<option value="">No plans returned by API</option>';
    }catch(error){
        select.innerHTML='<option value="">Unable to load plans</option>';
        setMessage("subscription-message",error.message,"error");
    }
}
function renderStatus(data){
    const source=data.onboarding||data.statuses||data;
    const statuses=[
        ["Subscription",pick(source,["subscription_status","subscription","subscription_state"])],
        ["KYC",pick(source,["kyc_status","kyc","identity_status"])],
        ["Payment",pick(source,["payment_status","payment","billing_status"])],
        ["Broker",pick(source,["broker_status","mt5_status","broker","mt5"])],
        ["Admin approval",pick(source,["admin_status","admin_approval","approval_status"])]
    ];
    const container=document.getElementById("status-cards");
    container.innerHTML="";
    for(const [label,value] of statuses){
        const card=document.createElement("div");
        card.className="status-card";
        card.dataset.state=value.toLowerCase();
        card.innerHTML=`<span>${label}</span><strong>${value}</strong>`;
        container.appendChild(card);
    }
    const activation=pick(source,["activation_status","copy_trading_status","status"],"PENDING");
    document.getElementById("activation-status").textContent=activation;
    const activated=source.copy_trading_active===true||source.is_active===true||
        ["ACTIVE","ACTIVATED","COMPLETE","APPROVED"].includes(activation);
    document.getElementById("dashboard-link").hidden=!activated;
    setMessage("status-message",
        activated?"Onboarding is complete. Your dashboard is available.":
        "Complete the outstanding steps and wait for administrative approval.",
        activated?"success":"");
}
async function refreshStatus(){
    const id=subscriberId();
    if(!id)return;
    const button=document.getElementById("refresh-status");
    button.disabled=true;button.textContent="Refreshing...";
    try{
        const statusData=await apiRequest(`/onboarding/${id}`,{headers:subscriberHeaders()});
        renderStatus(statusData);
        updateRegistrationStepStates(statusData.onboarding||statusData.statuses||statusData);
    }catch(error){setMessage("status-message",error.message,"error");}
    finally{button.disabled=false;button.textContent="Refresh status";}
}
function showRegistration(){
    const registrationPanel=document.getElementById("registration-panel");
    if(registrationPanel)registrationPanel.hidden=false;
    document.getElementById("login-panel").hidden=true;
    document.getElementById("workflow").hidden=true;
    document.getElementById("subscriber-logout").hidden=true;
    document.getElementById("registration-settings-button").hidden=false;
    document.getElementById("activation-progress").hidden=true;
    initializeRegistrationNavigation();
    closeRegistrationSettings();
}

document.getElementById("show-registration")?.addEventListener("click",showRegistration);
document.getElementById("show-login")?.addEventListener("click",showLogin);

document.getElementById("subscriber-registration-form")?.addEventListener("submit",async event=>{
    event.preventDefault();
    const button=document.getElementById("subscriber-registration-button");
    const name=document.getElementById("registration-name").value.trim();
    const email=document.getElementById("registration-email").value.trim().toLowerCase();
    const password=document.getElementById("registration-password").value;
    const confirmPassword=document.getElementById("registration-confirm-password").value;
    const consent=document.getElementById("registration-consent").checked;

    setMessage("subscriber-registration-message","");
    if(name.length<2){setMessage("subscriber-registration-message","Enter your full name.","error");return;}
    if(password.length<12){setMessage("subscriber-registration-message","Password must contain at least 12 characters.","error");return;}
    if(!/[a-z]/.test(password)||!/[A-Z]/.test(password)||!/[0-9]/.test(password)||!/[^A-Za-z0-9]/.test(password)){setMessage("subscriber-registration-message","Password must include uppercase, lowercase, a number and a special character.","error");return;}
    if(password!==confirmPassword){setMessage("subscriber-registration-message","Passwords do not match.","error");return;}
    if(!consent){setMessage("subscriber-registration-message","Confirm the registration declaration to continue.","error");return;}

    const registrationForm=event.currentTarget;
    button.disabled=true;
    button.textContent="Creating account...";
    try{
        const response=await fetch(ONBOARDING_API+"/copytrading/auth/register",{
            method:"POST",
            headers:{"Accept":"application/json","Content-Type":"application/json"},
            body:JSON.stringify({name,email,password})
        });
        let data={};
        try{data=await response.json();}catch(_){}
        if(!response.ok)throw new Error(data.detail||data.message||`Registration failed (${response.status})`);

        document.getElementById("subscriber-email").value=email;
        registrationForm.reset();
        showLogin();
        setMessage("subscriber-login-error","Account created successfully. Enter your password to sign in.","success");
        document.getElementById("subscriber-password").focus();
    }catch(error){
        setMessage("subscriber-registration-message",error.message,"error");
    }finally{
        button.disabled=false;
        button.textContent="Create account";
    }
});
document.getElementById("subscriber-login-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const button=document.getElementById("subscriber-login-button");
    const email=document.getElementById("subscriber-email").value.trim();
    const password=document.getElementById("subscriber-password").value;
    button.disabled=true;button.textContent="Signing in...";
    setMessage("subscriber-login-error","");
    try{
        const data=await parseResponse(await fetch(ONBOARDING_API+"/copytrading/auth/login",{
            method:"POST",
            headers:{"Accept":"application/json","Content-Type":"application/json"},
            body:JSON.stringify({email,password})
        }));
        if(!data.access_token||!data.subscriber_id)throw new Error("Subscriber login response is incomplete.");
        saveSubscriberSession(data);showWorkflow();
        await Promise.all([loadPlans(),refreshStatus()]);
    }catch(error){
        clearSubscriberSession();setMessage("subscriber-login-error",error.message,"error");
    }finally{button.disabled=false;button.textContent="Sign in";}
});
document.getElementById("subscription-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const button=event.submitter;
    const planId=Number(document.getElementById("plan-select").value);
    button.disabled=true;setMessage("subscription-message","Saving subscription...");
    try{
        await apiRequest(`/onboarding/${subscriberId()}/subscription`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({plan_id:planId})
        });
        setMessage("subscription-message","Subscription saved.","success");await refreshStatus();
    }catch(error){setMessage("subscription-message",error.message,"error");}
    finally{button.disabled=false;}
});
const PLATFORM_NAMES={MT4:"MetaTrader 4",MT5:"MetaTrader 5",CTRADER:"cTrader",MATCH_TRADER:"Match-Trader"};
function updateTradingPlatformForm(){
    const platform=document.getElementById("trading-platform")?.value||"MT5";
    const name=PLATFORM_NAMES[platform]||platform;
    document.getElementById("trading-account-label").textContent=`${name} account number or ID`;
    document.getElementById("trading-server-label").textContent=
        platform==="CTRADER"?"cTrader broker environment":
        platform==="MATCH_TRADER"?"Match-Trader broker URL or environment":
        `${name} server`;
}
function updateAccountPathway(){
    const capital=Number(document.getElementById("starting-capital")?.value||0);
    const accountType=document.getElementById("trading-account-type");
    if(capital>0){
        accountType.value=capital<1000?"CENT":"STANDARD";
    }
    const isCent=accountType.value==="CENT";
    const platform=document.getElementById("trading-platform").value;
    const supported=platform==="MT4"||platform==="MT5";
    setMessage(
        "trading-account-message",
        isCent&&!supported?"Cent accounts below USD 1,000 currently require MT4 or MT5.":"",
        isCent&&!supported?"error":""
    );
}
document.getElementById("trading-platform")?.addEventListener("change",()=>{updateTradingPlatformForm();updateAccountPathway();});
document.getElementById("starting-capital")?.addEventListener("input",updateAccountPathway);
document.getElementById("trading-account-type")?.addEventListener("change",updateAccountPathway);
updateTradingPlatformForm();
updateAccountPathway();
document.getElementById("trading-account-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const button=event.submitter;
    const platform=document.getElementById("trading-platform").value;
    const platformName=PLATFORM_NAMES[platform]||platform;
    const payload={
        platform,
        broker:document.getElementById("trading-broker").value.trim(),
        login:document.getElementById("trading-account").value.trim(),
        server:document.getElementById("trading-server").value.trim(),
        account_type:document.getElementById("trading-account-type").value,
        starting_capital_usd:Number(document.getElementById("starting-capital").value)
    };
    button.disabled=true;setMessage("trading-account-message",`Linking ${platformName} account...`);
    try{
        const account=await apiRequest(`/broker-accounts/link/${subscriberId()}`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify(payload)
        });
        const pending=account.status==="PENDING_AUTHORIZATION";
        setMessage(
            "trading-account-message",
            pending?`${platformName} account saved. Secure platform authorization is still required.`:
                `${platformName} ${account.account_type==="CENT"?"cent ":""}account verified and connected.`,
            pending?"":"success"
        );
        await refreshStatus();
    }catch(error){setMessage("trading-account-message",error.message,"error");}
    finally{button.disabled=false;}
});
async function requestSumsubToken(){
    return apiRequest(`/kyc/${subscriberId()}/access-token`,{
        method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({})
    });
}

function launchSumsubWebSdk(accessToken){
    if(typeof snsWebSdk==="undefined")throw new Error("Sumsub verification interface is unavailable.");

    const instance=snsWebSdk
        .init(accessToken,async()=>{
            const refreshed=await requestSumsubToken();
            return refreshed.token;
        })
        .withConf({lang:"en",theme:"dark"})
        .withOptions({addViewportTag:false,adaptIframeHeight:true})
        .on("idCheck.onError",error=>
            setMessage("kyc-message",error?.message||"KYC verification error","error")
        )
        .onMessage(type=>{
            if(type==="idCheck.applicantStatus"||
               type==="idCheck.onApplicantSubmitted"){
                setMessage(
                    "kyc-message",
                    "Identity verification submitted. Awaiting secure review.",
                    "success"
                );
                refreshStatus();
            }
        })
        .build();

    instance.launch("#sumsub-websdk-container");
}
document.getElementById("kyc-submit-button").addEventListener("click",async event=>{
    const button=event.currentTarget;
    button.disabled=true;setMessage("kyc-message","Opening secure identity verification...");
    try{
        const data=await requestSumsubToken();
        if(!data.token)throw new Error("KYC token response is incomplete.");
        launchSumsubWebSdk(data.token);
        setMessage("kyc-message","Complete the verification steps below.","success");
    }catch(error){setMessage("kyc-message",error.message,"error");}
    finally{button.disabled=false;}
});
// Owner promotions are applied only from the authenticated admin service.
document.getElementById("paypal-pay-button").addEventListener("click",async event=>{
    const button=event.currentTarget;
    button.disabled=true;setMessage("paypal-payment-message","Creating PayPal sandbox checkout...");
    try{
        const data=await apiRequest(`/payments/paypal/${subscriberId()}/order`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({})
        });
        const link=document.getElementById("paypal-checkout-link");
        link.href=data.approval_url;link.hidden=false;
        sessionStorage.setItem("bethel_paypal_order",data.order_id);
        setMessage("paypal-payment-message",`PayPal order created for ${data.amount} ${data.currency}.`,"success");
        window.open(data.approval_url,"_blank","noopener");
    }catch(error){setMessage("paypal-payment-message",error.message,"error");}
    finally{button.disabled=false;}
});

document.getElementById("wise-instructions-button").addEventListener("click",async event=>{
    const button=event.currentTarget;
    button.disabled=true;setMessage("wise-payment-message","Loading Wise transfer details...");
    try{
        const data=await apiRequest(`/payments/wise/${subscriberId()}/instructions`,{
            headers:subscriberHeaders()
        });
        const box=document.getElementById("wise-instructions");
        box.textContent=`Recipient: ${data.recipient_name} | Bank: ${data.bank_name} | Account: ${data.account_number||data.iban} | SWIFT/BIC: ${data.swift_bic||"N/A"} | Amount: ${data.amount} ${data.plan_currency}`;
        box.hidden=false;
        setMessage("wise-payment-message","Use the exact details and amount shown above.","success");
    }catch(error){setMessage("wise-payment-message",error.message,"error");}
    finally{button.disabled=false;}
});

document.getElementById("wise-submit-button").addEventListener("click",async event=>{
    const button=event.currentTarget;
    const reference=document.getElementById("wise-reference").value.trim();
    if(!reference){setMessage("wise-payment-message","Enter the Wise transfer reference.","error");return;}
    button.disabled=true;setMessage("wise-payment-message","Submitting Wise transfer...");
    try{
        await apiRequest(`/payments/wise/${subscriberId()}/submit`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({reference})
        });
        setMessage("wise-payment-message","Wise transfer submitted for administrator verification.","success");
        await refreshStatus();
    }catch(error){setMessage("wise-payment-message",error.message,"error");}
    finally{button.disabled=false;}
});

document.getElementById("payment-form").addEventListener("submit",async event=>{
    event.preventDefault();
    const button=event.submitter;
    const reference=document.getElementById("payment-reference").value.trim();
    button.disabled=true;setMessage("payment-message","Submitting payment reference...");
    try{
        await apiRequest(`/onboarding/${subscriberId()}/payment/submit`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({reference})
        });
        setMessage("payment-message","Payment submitted for admin verification.","success");
        await refreshStatus();
    }catch(error){setMessage("payment-message",error.message,"error");}
    finally{button.disabled=false;}
});

document.getElementById("stripe-pay-button").addEventListener("click",async event=>{
    const button=event.currentTarget;
    button.disabled=true;setMessage("stripe-payment-message","Creating secure card checkout...");
    try{
        const data=await apiRequest(`/payments/stripe/${subscriberId()}/checkout`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({})
        });
        if(!data.checkout_url)throw new Error("Stripe returned no checkout URL.");
        const link=document.getElementById("stripe-checkout-link");
        link.href=data.checkout_url;link.hidden=false;
        setMessage("stripe-payment-message",`Card checkout created for ${data.amount} ${data.currency}.`,"success");
        window.open(data.checkout_url,"_blank","noopener");
    }catch(error){setMessage("stripe-payment-message",error.message,"error");}
    finally{button.disabled=false;}
});

document.getElementById("binance-pay-button").addEventListener("click",async event=>{
    const button=event.currentTarget;
    button.disabled=true;setMessage("binance-payment-message","Creating secure USDT checkout...");
    try{
        const data=await apiRequest(`/payments/binance/${subscriberId()}/order`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({})
        });
        if(!data.checkout_url)throw new Error("Binance Pay returned no checkout URL.");
        const link=document.getElementById("binance-checkout-link");
        link.href=data.checkout_url;link.hidden=false;
        setMessage("binance-payment-message",`Binance Pay order created${data.amount?` for ${data.amount} ${data.currency||"USDT"}`:""}.`,"success");
        window.open(data.checkout_url,"_blank","noopener");
    }catch(error){setMessage("binance-payment-message",error.message,"error");}
    finally{button.disabled=false;}
});


let currentLegalDocumentIds=[];
async function loadLegalDocuments(){
 if(!subscriberToken()||!subscriberId())return;
 try{
  const [documents,status]=await Promise.all([
   apiRequest("/legal/documents"),
   apiRequest(`/legal/${subscriberId()}/status`,{headers:subscriberHeaders()})
  ]);
  const statusById=new Map((status.documents||[]).map(row=>[Number(row.document_id),row]));
  currentLegalDocumentIds=(documents.documents||[]).map(row=>Number(row.id));
  const container=document.getElementById("legal-documents");
  container.replaceChildren();
  (documents.documents||[]).forEach(document=>{
   const details=window.document.createElement("details");
   details.className="legal-document";
   const summary=window.document.createElement("summary");
   const accepted=statusById.get(Number(document.id))?.accepted;
   summary.textContent=`${document.title} â€” ${document.version}${accepted?" âœ“ Accepted":""}`;
   const content=window.document.createElement("pre");
   content.textContent=document.content;
   details.append(summary,content);container.append(details);
  });
  if(status.complete){
   const checkbox=document.getElementById("legal-consent-checkbox");
   const button=document.getElementById("accept-legal-documents");
   checkbox.checked=true;checkbox.disabled=true;button.disabled=true;button.textContent="Legal documents accepted";
  }
 }catch(error){setMessage("legal-consent-message",error.message,"error")}
}
document.getElementById("accept-legal-documents").addEventListener("click",async event=>{
 if(!document.getElementById("legal-consent-checkbox").checked){setMessage("legal-consent-message","Read the documents and tick the acceptance box first.","error");return}
 const button=event.currentTarget;button.disabled=true;
 try{
  await apiRequest(`/legal/${subscriberId()}/accept`,{
   method:"POST",headers:subscriberHeaders(true),
   body:JSON.stringify({accepted:true,document_ids:currentLegalDocumentIds})
  });
  setMessage("legal-consent-message","All current legal documents accepted.","success");
  await Promise.all([loadLegalDocuments(),refreshStatus()]);
 }catch(error){setMessage("legal-consent-message",error.message,"error");button.disabled=false}
});

async function loadProfitShare(){
 if(!subscriberToken()||!subscriberId())return;
 try{
  const data=await apiRequest(`/profit-share/${subscriberId()}`,{headers:subscriberHeaders()});
  const button=document.getElementById("accept-profit-share");
  const consent=document.getElementById("profit-share-consent");
  if(data.accepted){button.disabled=true;button.textContent="Agreement accepted";consent.checked=true;consent.disabled=true}
  const account=data.account;
  document.getElementById("profit-share-summary").textContent=account
   ?`Realized net profit: ${account.cumulative_net_profit} ${account.currency} | High-water mark: ${account.high_water_mark} | Projected 20% fee: ${account.projected_fee} ${account.currency}`
   :"No profit-share calculations begin until the agreement is accepted.";
 }catch(error){setMessage("profit-share-message",error.message,"error")}
}
document.getElementById("accept-profit-share").addEventListener("click",async event=>{
 if(!document.getElementById("profit-share-consent").checked){setMessage("profit-share-message","Tick the acceptance box first.","error");return}
 const button=event.currentTarget;button.disabled=true;
 try{
  await apiRequest(`/profit-share/${subscriberId()}/accept`,{
   method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({accepted:true})
  });
  setMessage("profit-share-message","20% profit-share agreement accepted.","success");
  await Promise.all([loadProfitShare(),refreshStatus()]);
 }catch(error){setMessage("profit-share-message",error.message,"error");button.disabled=false}
});

document.getElementById("refresh-status").addEventListener("click",refreshStatus);
document.getElementById("subscriber-logout").addEventListener("click",()=>{clearSubscriberSession();showLogin();});

const REGISTRATION_STEPS=[
    {step:3,displayStep:1,label:"Plan",description:"Select service plan",target:"registration-step-3"},
    {step:4,displayStep:2,label:"Identity",description:"Identity verification",target:"registration-step-4"},
    {step:5,displayStep:3,label:"Broker",description:"Link standard or cent account",target:"registration-step-5"},
    {step:6,displayStep:4,label:"Legal",description:"Accept agreements",target:"legal-consent-panel"},
    {step:7,displayStep:5,label:"Fees",description:"Profit-share terms",target:"profit-share-panel"},
    {step:8,displayStep:6,label:"Payment",description:"Confirm subscription",target:"registration-step-8"},
    {step:9,displayStep:7,label:"Review",description:"Compliance review",target:"registration-step-9"},
    {step:10,displayStep:8,label:"Active",description:"Dashboard access",target:"registration-step-9"}
];

function markProgressStep(step){
    const visibleStep=Math.min(8,Math.max(1,Number(step)-2));
    document.querySelectorAll(".progress-item").forEach((item,index)=>{
        const active=index+1===visibleStep;
        item.classList.toggle("current",active);
        item.setAttribute("aria-current",active?"step":"false");
    });
}
function closeRegistrationSettings(){
    const panel=document.getElementById("registration-settings");
    const button=document.getElementById("registration-settings-button");
    if(panel)panel.hidden=true;
    if(button)button.setAttribute("aria-expanded","false");
}
function toggleRegistrationSettings(){
    const panel=document.getElementById("registration-settings");
    const button=document.getElementById("registration-settings-button");
    if(!panel||!button)return;
    initializeRegistrationNavigation();
    panel.hidden=!panel.hidden;
    button.setAttribute("aria-expanded",String(!panel.hidden));
    if(!panel.hidden)panel.scrollIntoView({behavior:"smooth",block:"start"});
}
function openRegistrationStep(step,scroll=true){
    const requested=Math.min(10,Math.max(3,Number(step)||3));
    const definition=REGISTRATION_STEPS.find(item=>item.step===requested);
    if(!definition?.target||!subscriberToken())return;
    document.querySelectorAll(".registration-step-panel").forEach(panel=>panel.hidden=true);
    const panel=document.getElementById(definition.target);
    if(!panel)return;
    panel.hidden=false;
    panel.dataset.visibleRegistrationStep=String(definition.displayStep);
    sessionStorage.setItem("bethel_registration_step",String(requested));
    markProgressStep(requested);
    document.querySelectorAll(".registration-step-button").forEach(button=>{
        const active=Number(button.dataset.step)===requested;
        button.classList.toggle("active",active);
        button.setAttribute("aria-current",active?"step":"false");
    });
    closeRegistrationSettings();
    if(scroll)panel.scrollIntoView({behavior:"smooth",block:"start"});
}
function createNavigationButton(menu,{label,description,number,onClick,active=false}){
    const button=document.createElement("button");
    button.type="button";
    button.className="registration-step-button";
    button.innerHTML=`<span>${number}</span><strong>${label}</strong><small>${description}</small>`;
    button.classList.toggle("active",active);
    button.addEventListener("click",onClick);
    menu.appendChild(button);
    return button;
}
function initializeRegistrationNavigation(){
    const menu=document.getElementById("registration-step-menu");
    if(!menu)return;
    menu.replaceChildren();
    if(!subscriberToken()){
        createNavigationButton(menu,{number:"⌂",label:"Home",description:"Return to the public website",onClick:()=>{window.location.href="https://betheltradingtechnologies.com/";}});
        createNavigationButton(menu,{number:"1",label:"Register",description:"Create a new Bethel account",active:!document.getElementById("registration-panel").hidden,onClick:showRegistration});
        createNavigationButton(menu,{number:"→",label:"Subscriber login",description:"Access an existing account",active:!document.getElementById("login-panel").hidden,onClick:showLogin});
        return;
    }
    REGISTRATION_STEPS.forEach(item=>{
        const button=createNavigationButton(menu,{
            number:String(item.displayStep),
            label:item.label,
            description:item.description,
            onClick:()=>openRegistrationStep(item.step)
        });
        button.dataset.step=String(item.step);
    });
    document.querySelectorAll(".progress-item").forEach((item,index)=>{
        const step=index+3;
        item.tabIndex=0;
        item.setAttribute("role","button");
        item.onclick=()=>openRegistrationStep(step);
        item.onkeydown=event=>{
            if(event.key==="Enter"||event.key===" "){event.preventDefault();openRegistrationStep(step);}
        };
    });
}

function updateRegistrationStepStates(source={}){
    const complete={
        3:["ACTIVE","APPROVED","COMPLETE","PAID"].includes(pick(source,["subscription_status","subscription","subscription_state"])),
        4:["APPROVED","COMPLETE","VERIFIED"].includes(pick(source,["kyc_status","kyc","identity_status"])),
        5:["CONNECTED","COMPLETE","APPROVED"].includes(pick(source,["broker_status","mt5_status","broker","mt5"])),
        8:["PAID","COMPLETE","APPROVED"].includes(pick(source,["payment_status","payment","billing_status"])),
        9:["APPROVED","COMPLETE","ACTIVE"].includes(pick(source,["admin_status","admin_approval","approval_status"])),
        10:["ACTIVE","ACTIVATED","COMPLETE","APPROVED"].includes(pick(source,["activation_status","copy_trading_status","status"]))
    };
    document.querySelectorAll(".registration-step-button").forEach(button=>{
        if(complete[Number(button.dataset.step)])button.classList.add("complete");
    });
}

document.getElementById("registration-settings-button")?.addEventListener("click",toggleRegistrationSettings);
document.getElementById("close-registration-settings")?.addEventListener("click",closeRegistrationSettings);
document.getElementById("header-registration-button")?.addEventListener("click",showRegistration);
document.getElementById("header-login-button")?.addEventListener("click",showLogin);


(async function(){
    if(subscriberToken()&&subscriberId()){
        showWorkflow();await Promise.all([loadPlans(),refreshStatus(),loadProfitShare(),loadLegalDocuments()]);
    }else showRegistration();
})();


window.addEventListener("load",async()=>{
    const params=new URLSearchParams(window.location.search);
    if(params.get("payment")!=="paypal-success"||!subscriberToken()||!subscriberId())return;
    const orderId=params.get("token")||sessionStorage.getItem("bethel_paypal_order");
    if(!orderId)return;
    setMessage("paypal-payment-message","Confirming PayPal payment...");
    try{
        await apiRequest(`/payments/paypal/${subscriberId()}/capture/${encodeURIComponent(orderId)}`,{
            method:"POST",headers:subscriberHeaders(true),body:JSON.stringify({})
        });
        sessionStorage.removeItem("bethel_paypal_order");
        setMessage("paypal-payment-message","PayPal payment confirmed.","success");
        await refreshStatus();
    }catch(error){setMessage("paypal-payment-message",error.message,"error");}
});



