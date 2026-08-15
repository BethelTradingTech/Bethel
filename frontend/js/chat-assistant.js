(function(){
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
      <input class="bethel-chat-input" maxlength="1000" autocomplete="off" placeholder="Ask a question…" aria-label="Your question">
      <button class="bethel-chat-send" type="submit">Send</button>
    </form>
    <div class="bethel-chat-note">General information only. For account-specific help, email <a href="mailto:${SUPPORT}">${SUPPORT}</a>.</div>`;

  document.body.appendChild(panel);
  document.body.appendChild(launcher);

  const messages=panel.querySelector(".bethel-chat-messages");
  const form=panel.querySelector(".bethel-chat-form");
  const input=panel.querySelector(".bethel-chat-input");
  const send=panel.querySelector(".bethel-chat-send");

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

  addMessage("Hello! I’m the Bethel website assistant. Ask me a quick question about Bethel, registration, services or general support.","bot");

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
      addMessage(data.answer||`I can’t confirm that right now. Please email ${SUPPORT}.`,"bot");
    }catch(_){
      addMessage(`I’m unable to answer that right now. Please email ${SUPPORT} and the Bethel team can help you.`,"bot");
    }finally{
      input.disabled=false;send.disabled=false;input.focus();
    }
  });
})();
