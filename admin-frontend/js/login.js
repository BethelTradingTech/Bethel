const API_BASE =
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1" ||
    window.location.hostname.startsWith("192.168.")
        ? `${window.location.protocol}//${window.location.hostname}:8000`
        : window.location.hostname === "bethel-api.onrender.com" ||
          window.location.hostname === "api.betheltradingtechnologies.com"
            ? window.location.origin
            : "https://bethel-api.onrender.com";

function safeNextPage() {
    const requested = new URLSearchParams(window.location.search).get("next") || "";
    const allowed = new Set([
        "index.html",
        "package-routing.html",
        "promotions.html"
    ]);
    return allowed.has(requested) ? requested : "index.html";
}

if (isAuthenticated()) {
    window.location.replace(safeNextPage());
}

document.getElementById("login-form").addEventListener("submit", async (event) => {
    event.preventDefault();

    const button = document.getElementById("login-button");
    const error = document.getElementById("login-error");
    const identifier = document.getElementById("identifier").value.trim();
    const password = document.getElementById("password").value;

    button.disabled = true;
    button.innerText = "Signing in...";
    error.innerText = "";

    try {
        const response = await fetch(API_BASE + "/auth/login", {
            method: "POST",
            headers: {
                "Accept": "application/json",
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ identifier, password })
        });

        const data = await response.json();

        if (!response.ok || !data.access_token) {
            throw new Error(data.detail || "Unable to sign in");
        }

        if (!["admin", "super_admin"].includes(data.user?.role)) {
            throw new Error("This account does not have admin access");
        }

        saveToken(data.access_token);
        window.location.replace(safeNextPage());
    } catch (loginError) {
        error.innerText = loginError.message || "Unable to sign in";
        button.disabled = false;
        button.innerText = "Sign in";
    }
});
