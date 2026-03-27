(function () {
    const isIos = /iphone|ipad|ipod/i.test(window.navigator.userAgent || '');
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone === true;

    let deferredInstallPrompt = null;

    const state = {
        canInstall: false,
        isIos,
        isStandalone
    };

    function emitInstallState() {
        window.dispatchEvent(new CustomEvent('pwa-install-availability', { detail: { ...state } }));
    }

    window.getPwaInstallState = function () {
        return { ...state };
    };

    window.triggerPwaInstall = async function () {
        if (deferredInstallPrompt) {
            deferredInstallPrompt.prompt();
            const result = await deferredInstallPrompt.userChoice;
            deferredInstallPrompt = null;
            state.canInstall = false;
            emitInstallState();
            return result.outcome;
        }

        if (state.isIos && !state.isStandalone) {
            window.alert('To install FinApp on iPhone/iPad: tap Share in Safari, then choose Add to Home Screen.');
            return 'ios-instructions';
        }

        return 'unavailable';
    };

    window.addEventListener('beforeinstallprompt', function (event) {
        event.preventDefault();
        deferredInstallPrompt = event;
        state.canInstall = true;
        emitInstallState();
    });

    window.addEventListener('appinstalled', function () {
        deferredInstallPrompt = null;
        state.canInstall = false;
        state.isStandalone = true;
        emitInstallState();
    });

    if ('serviceWorker' in navigator) {
        window.addEventListener('load', function () {
            navigator.serviceWorker.register('/service-worker.js', { scope: '/' })
                .catch(function (error) {
                    console.warn('Service worker registration failed:', error);
                });
        });
    }

    emitInstallState();
})();
