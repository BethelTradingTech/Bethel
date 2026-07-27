document.getElementById("forgot-password-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const message=document.getElementById("message");
  const button=event.submitter;
  button.disabled=true;message.textContent="Submitting…";
  try{
    const response=await fetch("/copytrading/auth/forgot-password",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({email:document.getElementById("email").value.trim()})
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||"Request failed");
    message.textContent=data.message;
  }catch(error){message.textContent=error.message}
  finally{button.disabled=false}
});
