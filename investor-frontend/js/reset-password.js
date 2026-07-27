document.getElementById("reset-password-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const message=document.getElementById("message");
  const button=event.submitter;
  const password=document.getElementById("password").value;
  const confirmation=document.getElementById("confirm-password").value;
  if(password!==confirmation){message.textContent="Passwords do not match.";return}
  const token=new URLSearchParams(location.search).get("token");
  if(!token){message.textContent="Reset token is missing.";return}
  button.disabled=true;message.textContent="Resetting password…";
  try{
    const response=await fetch("/copytrading/auth/reset-password",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({token,password})
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||"Reset failed");
    message.textContent=data.message+" Redirecting to sign in…";
    setTimeout(()=>location.href="onboarding.html",1200);
  }catch(error){message.textContent=error.message;button.disabled=false}
});
