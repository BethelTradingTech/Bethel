const token = new URLSearchParams(window.location.search).get("token") || "";
const form = document.getElementById("setup-form");
const message = document.getElementById("setup-message");
const loginLink = document.getElementById("login-link");

function showMessage(text, type = ""){
    message.textContent = text;
    message.className = `form-message ${type}`.trim();
}

if(!token){
    showMessage("This setup link is missing its security token.", "error");
    form.querySelector("button").disabled = true;
}

form.addEventListener("submit", async event => {
    event.preventDefault();
    const password = document.getElementById("password").value;
    const confirmation = document.getElementById("confirm-password").value;
    if(password !== confirmation){
        showMessage("The passwords do not match.", "error");
        return;
    }
    const button = form.querySelector("button");
    button.disabled = true;
    showMessage("Creating your password...");
    try{
        const response = await fetch("/copytrading/auth/setup-password", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({token, password})
        });
        const data = await response.json().catch(() => ({}));
        if(!response.ok){
            throw new Error(data.detail || "Password setup failed");
        }
        showMessage("Password created successfully. You can now sign in.", "success");
        form.querySelectorAll("input").forEach(input => input.disabled = true);
        loginLink.hidden = false;
    }catch(error){
        showMessage(error.message, "error");
        button.disabled = false;
    }
});
