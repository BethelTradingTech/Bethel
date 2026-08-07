/*
Bethel Trading Technologies
Admin Authentication Engine
*/


// ======================================
// TOKEN STORAGE
// ======================================


const TOKEN_KEY = "bethel_access_token";



// ======================================
// SAVE TOKEN
// ======================================


function saveToken(token){

    localStorage.setItem(
        TOKEN_KEY,
        token
    );

}



// ======================================
// GET TOKEN
// ======================================


function getToken(){

    return localStorage.getItem(
        TOKEN_KEY
    );

}



// ======================================
// LOGOUT
// ======================================


function logout(){

    localStorage.removeItem(
        TOKEN_KEY
    );


    window.location.href="login.html";

}



// ======================================
// DECODE JWT
// ======================================


function decodeToken(){

    const token = getToken();


    if(!token){

        return null;

    }


    try{


        const payload =
            token.split(".")[1]
                .replace(/-/g, "+")
                .replace(/_/g, "/");

        const paddedPayload =
            payload.padEnd(
                Math.ceil(payload.length / 4) * 4,
                "="
            );


        return JSON.parse(
            atob(paddedPayload)
        );


    }

    catch(error){


        console.error(
            "JWT Decode Error:",
            error
        );


        return null;

    }

}



// ======================================
// AUTH CHECK
// ======================================


function isAuthenticated(){


    const token = getToken();


    if(!token){

        return false;

    }


    const payload =
        decodeToken();



    if(!payload){

        return false;

    }

    if(!["admin", "super_admin"].includes(payload.role)){

        localStorage.removeItem(TOKEN_KEY);
        return false;

    }


    if(payload.exp){


        const now =
            Math.floor(
                Date.now()/1000
            );



        if(payload.exp < now){


            logout();


            return false;

        }

    }



    return true;

}


function requireAuthentication(){

    if(!isAuthenticated()){

        window.location.replace("login.html");

        return false;

    }

    return true;

}


// ======================================
// SUPER ADMIN RISK MONITOR EXTENSION
// ======================================
// Loaded only inside the protected admin application. The extension appends
// risk-monitoring UI to the existing Performance view and does not touch the
// investor or subscriber-facing applications.

function loadAdminRiskMonitor(){

    if(!isAuthenticated()){
        return;
    }

    if(document.querySelector('script[data-bethel-risk-monitor="true"]')){
        return;
    }

    const script = document.createElement("script");
    script.src = "js/risk-monitor.js?v=20260806-risk1";
    script.defer = true;
    script.dataset.bethelRiskMonitor = "true";
    script.onerror = () => console.error("Unable to load Bethel Super Admin risk monitor");
    document.head.appendChild(script);
}


if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", loadAdminRiskMonitor, {once:true});
}else{
    loadAdminRiskMonitor();
}
