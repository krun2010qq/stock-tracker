// Compatibility shim for browsers still loading the legacy app.js entry.
(function loadDashboard() {
  if (document.querySelector('script[src*="dashboard.js"]')) {
    return;
  }
  const script = document.createElement("script");
  script.src = "/static/dashboard.js?v=3.2.0";
  script.defer = true;
  document.body.appendChild(script);
})();
