(function(){
  // Keep Bethel's live public trading visibility immediately below the main hero.
  // The existing broadcaster/MT5 scripts still control whether live data is available.
  const hero=document.querySelector(".hero");
  const publicBroadcast=document.getElementById("public-broadcast");
  const publicMt5=document.getElementById("public-live-mt5");
  if(hero){
    let priorityAnchor=hero;
    [publicBroadcast,publicMt5].forEach((section)=>{
      if(section){
        priorityAnchor.insertAdjacentElement("afterend",section);
        priorityAnchor=section;
      }
    });
  }

  // Public-facing title for the read-only MT5 connector session.
  if(publicMt5){
    const heading=publicMt5.querySelector(".section-header h2");
    if(heading)heading.textContent="LIVE TRADE BROADCAST FROM BETHEL TERMINAL 1";
  }

  const API="https://api.betheltradingtechnologies.com/public/assistant/chat";
  const SUPPORT="info@betheltradingtechnologies.com";
  const launcher=document.createElement("button");
  launcher.className="bethel-chat-launcher";
  launcher.type="button";
  launcher.setAttribute("aria-label","Open Bethel website assistant");
  launcher.innerHTML='<i class="fa-solid fa-comments" aria-hidden="true"></i><span>Ask Bethel</span>';

  const panel=document.createElement("section");
  panel.className="bethel-chat-panel";
  panel.setAttribute("aria-label","Bethel website assistant");
  panel.innerHTML=`
    <div class="bethel-chat-header">
      <div><div class="bethel-chat-title">Bethel Assistant</div><div class="bethel-chat-subtitle">Quick general questions</div></div>
      <button class="bethel-chat-close" type="button" aria-label="Close assistant">&times;</button>
    </div>
    <div class="bethel-chat-messages" aria-live="polite"></div>
    <form class="bethel-chat-form">
      <input class="bethel-chat-input" maxlength="500" autocomplete="off" placeholder="Ask a question…" aria-label="Your question">
      <button class="bethel-chat-send" type="submit">Send</button>
    </form>
    <div class="bethel-chat-note">For all inquiries, email <a href="mailto:${SUPPORT}">${SUPPORT}</a>. General information only.</div>`;

  document.body.appendChild(panel);
  document.body.appendChild(launcher);

  const messages=panel.querySelector(".bethel-chat-messages");
  const form=panel.querySelector(".bethel-chat-form");
  const input=panel.querySelector(".bethel-chat-input");
  const send=panel.querySelector(".bethel-chat-send");

  function ensureSupportEmail(text){
    const value=String(text||"").trim();
    if(value.toLowerCase().includes(SUPPORT.toLowerCase()))return value;
    return (value?value+"\n\n":"")+"For further inquiries, email: "+SUPPORT;
  }

  function addMessage(text,who){
    const item=document.createElement("div");
    item.className="bethel-chat-message "+who;
    const parts=String(text).split(SUPPORT);
    parts.forEach((part,index)=>{
      item.appendChild(document.createTextNode(part));
      if(index<parts.length-1){const a=document.createElement("a");a.href="mailto:"+SUPPORT;a.textContent=SUPPORT;item.appendChild(a);}
    });
    messages.appendChild(item);
    messages.scrollTop=messages.scrollHeight;
  }

  addMessage(ensureSupportEmail("Hello! I’m the Bethel website assistant. Ask me a quick question about Bethel, registration, services or general support."),"bot");

  launcher.addEventListener("click",()=>{panel.classList.toggle("open");if(panel.classList.contains("open"))input.focus();});
  panel.querySelector(".bethel-chat-close").addEventListener("click",()=>panel.classList.remove("open"));

  form.addEventListener("submit",async(event)=>{
    event.preventDefault();
    const question=input.value.trim();
    if(!question)return;
    addMessage(question,"user");
    input.value=""; input.disabled=true; send.disabled=true;
    try{
      const response=await fetch(API,{method:"POST",headers:{"Content-Type":"application/json","Accept":"application/json"},body:JSON.stringify({message:question})});
      const data=await response.json().catch(()=>({}));
      if(!response.ok)throw new Error(data.detail||"Assistant unavailable");
      addMessage(ensureSupportEmail(data.answer||"I can’t confirm that right now."),"bot");
    }catch(_){
      addMessage(ensureSupportEmail("I’m unable to answer that right now. The Bethel team can help you."),"bot");
    }finally{
      input.disabled=false;send.disabled=false;input.focus();
    }
  });

  if(!document.querySelector('link[href*="visitor-reviews.css"]')){const l=document.createElement("link");l.rel="stylesheet";l.href="css/visitor-reviews.css?v=1";document.head.appendChild(l);}
  if(!document.querySelector('script[src*="visitor-reviews.js"]')){const s=document.createElement("script");s.src="js/visitor-reviews.js?v=1";s.defer=true;document.body.appendChild(s);}
})();
