(() => {
  const load = (src) => {
    if (document.querySelector(`script[src^="${src}"]`)) return;
    const script = document.createElement('script');
    script.src = src;
    script.defer = true;
    document.head.appendChild(script);
  };
  load('js/language-selector.js?v=20260916');
})();
