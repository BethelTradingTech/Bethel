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
// SUPER ADMIN EXTENSIONS
// ======================================
// These scripts run only inside the authenticated admin application. They do
// not weaken backend API protection and do not modify investor/subscriber pages.

function loadAdminExtension(src, dataKey, errorMessage){

    if(!isAuthenticated()){
        return;
    }

    if(document.querySelector(`script[data-${dataKey}="true"]`)){
        return;
    }

    const script = document.createElement("script");
    script.src = src;
    script.defer = true;
    script.setAttribute(`data-${dataKey}`, "true");
    script.onerror = () => console.error(errorMessage);
    document.head.appendChild(script);
}

function loadAdminExtensions(){
    loadAdminExtension(
        "js/risk-monitor.js?v=20260807-risk3",
        "bethel-risk-monitor",
        "Unable to load Bethel Super Admin risk monitor"
    );
    loadAdminExtension(
        "js/performance-growth.js?v=20260807-growth5",
        "bethel-performance-growth",
        "Unable to load Bethel Super Admin account growth chart"
    );
    loadAdminExtension(
        "js/refresh-current-view.js?v=20260806-refresh1",
        "bethel-session-refresh",
        "Unable to load Bethel Super Admin refresh control"
    );
    loadAdminExtension(
        "js/traffic-analytics.js?v=20260808-traffic1",
        "bethel-traffic-analytics",
        "Unable to load Bethel Super Admin traffic analytics"
    );
}


if(document.readyState === "loading"){
    document.addEventListener("DOMContentLoaded", loadAdminExtensions, {once:true});
}else{
    loadAdminExtensions();
}
