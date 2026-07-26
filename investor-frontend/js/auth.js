const INVESTOR_TOKEN_KEY = "bethel_investor_access_token";


function getInvestorToken(){
    return localStorage.getItem(INVESTOR_TOKEN_KEY);
}


function saveInvestorToken(token){
    localStorage.setItem(INVESTOR_TOKEN_KEY, token);
}


function clearInvestorToken(){
    localStorage.removeItem(INVESTOR_TOKEN_KEY);
}


function decodeInvestorToken(){
    const token = getInvestorToken();
    if(!token){
        return null;
    }

    try {
        const segment = token
            .split(".")[1]
            .replace(/-/g, "+")
            .replace(/_/g, "/");
        const padded = segment.padEnd(
            Math.ceil(segment.length / 4) * 4,
            "="
        );
        return JSON.parse(atob(padded));
    } catch(error) {
        return null;
    }
}


function getInvestorSession(){
    const payload = decodeInvestorToken();
    if(
        !payload ||
        payload.role !== "investor" ||
        !payload.investor_id ||
        (payload.exp && payload.exp < Math.floor(Date.now() / 1000))
    ){
        clearInvestorToken();
        return null;
    }
    return payload;
}


function investorLogout(){
    clearInvestorToken();
    window.location.replace("login.html");
}
