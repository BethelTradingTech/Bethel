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

    if(payload.role !== "admin"){

        localStorage.removeItem(TOKEN_KEY);
        return false;

    }

    if(payload.role !== "admin"){

        localStorage.removeItem(TOKEN_KEY);
        return false;

    }

    if(payload.role !== "admin"){

        localStorage.removeItem(TOKEN_KEY);
        return false;

    }

    if(payload.role !== "admin"){

        localStorage.removeItem(TOKEN_KEY);
        return false;

    }

    if(payload.role !== "admin"){

        localStorage.removeItem(TOKEN_KEY);
        return false;

    }

    if(payload.role !== "admin"){

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
