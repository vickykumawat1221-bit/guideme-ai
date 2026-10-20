// Optional runtime configuration. `start.sh` rewrites this file with the port it
// actually uses so the static frontend always finds the API.
//
// You can also override it from the browser console:
//   localStorage.setItem("gm_api", "https://your-api.example.com");
window.GM_API_BASE = window.GM_API_BASE || "";
