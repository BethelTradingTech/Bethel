const INVESTOR_API =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "https://api.betheltradingtechnologies.com";


if(getInvestorSession()){
    window.location.replace("index.html");
}


document.getElementById("login-form").addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const button = document.getElementById("login-button");
        const error = document.getElementById("login-error");
        const email = document.getElementById("email").value.trim();
        const password = document.getElementById("password").value;

        button.disabled = true;
        button.textContent = "Signing in...";
        error.textContent = "";

        try {
            const query = new URLSearchParams({email, password});
            const response = await fetch(
                INVESTOR_API + "/investor/auth/login?" + query,
                {
                    method: "POST",
                    headers: {"Accept": "application/json"}
                }
            );
            const data = await response.json();

            if(!response.ok || !data.access_token){
                throw new Error(data.detail || "Unable to sign in");
            }

            saveInvestorToken(data.access_token);

            if(!getInvestorSession()){
                throw new Error("Invalid investor session");
            }

            window.location.replace("index.html");
        } catch(loginError) {
            clearInvestorToken();
            error.textContent = loginError.message || "Unable to sign in";
            button.disabled = false;
            button.textContent = "Sign in";
        }
    }
);
