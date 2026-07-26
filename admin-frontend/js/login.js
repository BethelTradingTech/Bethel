const API_BASE =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1"
        ? "http://127.0.0.1:8000"
        : "https://api.betheltradingtechnologies.com";

if (isAuthenticated()) {
    window.location.replace("index.html");
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = document.getElementById("login-button");
    const error = document.getElementById("login-error");
    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    button.disabled = true;
    button.innerText = "Signing in...";
    error.innerText = "";

    try {
        const query = new URLSearchParams({ email, password });
        const response = await fetch(API_BASE + "/auth/login?" + query, {
            method: "POST",
            headers: { "Accept": "application/json" }
        });

        const data = await response.json();

        if (!response.ok || !data.access_token) {
            throw new Error(data.detail || "Unable to sign in");
        }

        if (data.user?.role !== "admin") {
            throw new Error("This account does not have admin access");
        }

        saveToken(data.access_token);
        window.location.replace("index.html");
    } catch (loginError) {
        error.innerText = loginError.message || "Unable to sign in";
        button.disabled = false;
        button.innerText = "Sign in";
    }
});
