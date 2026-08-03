const INVESTOR_API =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.startsWith("192.168.")
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : window.location.hostname === "bethel-api.onrender.com" ||
          window.location.hostname === "api.betheltradingtechnologies.com"
            ? window.location.origin
            : "https://bethel-api.onrender.com";


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
            const response = await fetch(
                INVESTOR_API + "/investor/auth/login",
                {
                    method: "POST",
                    headers: {
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({email, password})
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
