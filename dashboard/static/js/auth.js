/*
Bethel Trading Technologies
Investor Authentication Engine
Phase 7 Secure Frontend
*/


// ======================================
// TOKEN STORAGE
// ======================================


const TOKEN_KEY = "bethel_access_token";

// ======================================
// LOGIN
// ======================================


async function login(email,password){


    try{


        const response = await fetch(

            "/investor/auth/login?email=" +
            encodeURIComponent(email) +
            "&password=" +
            encodeURIComponent(password),

            {
                method:"POST"
            }

        );



        if(!response.ok){


            console.error(
                "Login failed:",
                response.status
            );


            return false;


        }



        const data =
            await response.json();



        if(data.access_token){


            saveToken(
                data.access_token
            );


            return true;


        }



        return false;


    }


    catch(error){


        console.error(
            "Login error:",
            error
        );


        return false;


    }


}


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


    window.location.href="/login";


}


// ======================================
// DECODE JWT
// ======================================


function decodeToken(){


    const token =
        getToken();



    if(!token){

        return null;

    }



    try{


        const payload =
            token.split(".")[1];



        return JSON.parse(

            atob(payload)

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
// GET INVESTOR ID
// ======================================


function getInvestorId(){


    const payload =
        decodeToken();



    if(!payload){

        return null;

    }



    return payload.investor_id ?? null;


}



// ======================================
// GET ROLE
// ======================================


function getRole(){


    const payload =
        decodeToken();



    if(!payload){

        return null;

    }



    return payload.role ?? null;


}


// ======================================
// AUTHENTICATION CHECK
// ======================================


function isAuthenticated(){


    const token =
        getToken();



    if(!token){

        return false;

    }



    const payload =
        decodeToken();



    if(!payload){

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


// ======================================
// REQUIRE LOGIN
// ======================================


function requireLogin(){


    if(!isAuthenticated()){


        window.location.href="/login";


        return false;


    }



    return true;


}


