/*
Bethel Trading Technologies
Secure API Gateway
Phase 7 Frontend Architecture
*/
// ======================================
// API BASE URL
// ======================================


const API_BASE =

(
    window.location.hostname === "localhost" ||

    window.location.hostname === "127.0.0.1"

)

?

"http://127.0.0.1:8000"

:

"https://api.betheltradingtechnologies.com";

// ======================================
// COMMON REQUEST ENGINE
// ======================================


async function apiRequest(
    method,
    url,
    data=null
){


    try{


        const headers = {

            "Content-Type":
                "application/json"

        };



        const token =
            getToken();



        if(token){


            headers["Authorization"] =
                "Bearer " + token;


        }



        const options = {

    method: method,

    headers: headers,

    credentials: "include"

};



        if(data){


            options.body =
                JSON.stringify(data);


        }




        const response =
            await fetch(

                API_BASE +

                url +

                "?t=" +

                Date.now(),

                options

            );





        if(response.status === 401){


            console.error(
                "Unauthorized API request:",
                url
            );


            return null;


        }





        if(!response.ok){


            console.error(
                "API ERROR:",
                response.status,
                url
            );


            return null;


        }





        return await response.json();


    }


    catch(error){


        console.error(

            "API REQUEST FAILED:",

            error

        );


        return null;


    }


}


// ======================================
// GET REQUEST
// ======================================


async function apiGet(url){


    return await apiRequest(

        "GET",

        url

    );


}


// ======================================
// POST REQUEST
// ======================================


async function apiPost(
    url,
    data
){


    return await apiRequest(

        "POST",

        url,

        data

    );


}


// ======================================
// PUT REQUEST
// ======================================


async function apiPut(
    url,
    data
){


    return await apiRequest(

        "PUT",

        url,

        data

    );


}



// ======================================
// DELETE REQUEST
// ======================================


async function apiDelete(url){


    return await apiRequest(

        "DELETE",

        url

    );


}


