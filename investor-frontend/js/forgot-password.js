const FORGOT_PASSWORD_API =
  window.location.hostname === "localhost" ||
  window.location.hostname === "127.0.0.1" ||
  window.location.hostname.startsWith("192.168.")
    ? `${window.location.protocol}//${window.location.hostname}:8000`
    : window.location.hostname === "api.betheltradingtechnologies.com"
      ? window.location.origin
      : "https://api.betheltradingtechnologies.com";

document.getElementById("forgot-password-form").addEventListener("submit",async event=>{
  event.preventDefault();
  const message=document.getElementById("message");
  const button=event.submitter;
  button.disabled=true;message.textContent="Submitting…";
  try{
    const response=await fetch(FORGOT_PASSWORD_API+"/copytrading/auth/forgot-password",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({email:document.getElementById("email").value.trim()})
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.detail||"Request failed");
    message.textContent=data.message;
  }catch(error){message.textContent=error.message}
  finally{button.disabled=false}
});
