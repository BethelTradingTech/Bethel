let deferredInstallPrompt = null;


function isIos(){
    return /iphone|ipad|ipod/i.test(navigator.userAgent);
}


function isStandalone(){
    return window.matchMedia("(display-mode: standalone)").matches ||
        window.navigator.standalone === true;
}


async function installBethelApp(){
    if(deferredInstallPrompt){
        deferredInstallPrompt.prompt();
        await deferredInstallPrompt.userChoice;
        deferredInstallPrompt = null;
        document.getElementById("install-app-button")?.remove();
        return;
    }

    if(isIos()){
        alert("On iPhone or iPad: tap Share, then choose Add to Home Screen.");
    }
}


if("serviceWorker" in navigator){
    window.addEventListener(
        "load",
        () => navigator.serviceWorker.register("./sw.js")
    );
}


window.addEventListener("beforeinstallprompt", event => {
    event.preventDefault();
    deferredInstallPrompt = event;
    document.getElementById("install-app-button")?.removeAttribute("hidden");
});


if(isIos() && !isStandalone()){
    document.getElementById("install-app-button")?.removeAttribute("hidden");
}


document.getElementById("install-app-button")?.addEventListener(
    "click",
    installBethelApp
);
