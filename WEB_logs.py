#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  WEB_logs.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

from   WEB_shared_css import SHARED_CSS

HTML_LOGS = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Info Center – Logs</title>
    <style>
""" + SHARED_CSS + """
    </style>
</head>
<body>
    <h1>Logs</h1>
    <div class="status" id="meta">Loading...</div>
    <button id="debugBtn" class="debug-off" onclick="toggleDebug()">DEBUG: --</button>
    <button id="webLogBtn" class="debug-off" onclick="toggleWebLogs()">WEB LOGS: OFF</button>
    <button id="pauseBtn" class="debug-off" onclick="togglePause()">PAUSE</button>
    <pre class="logbox" id="log"></pre>
    <button class="nav-btn" onclick="window.location='/'">← Back to Controls</button>
    <button class="nav-btn" onclick="window.location='/diag'">Diagnostics / Test</button>
    <button class="logout" onclick="logout()">Logout</button>
    <script>
        window._debug = false;
        window._webLogs = false;
        window._paused = false;
        const pre = document.getElementById("log");
        const debugBtn = document.getElementById("debugBtn");
        const webLogBtn = document.getElementById("webLogBtn");
        const pauseBtn = document.getElementById("pauseBtn");

        function logout() {
            fetch('/logout', {credentials: 'same-origin'})
                .then(() => window.location = '/login');
        }
        function toggleDebug() {
            fetch('/set_debug?value=' + (window._debug ? 0 : 1), {method: 'POST', credentials: 'same-origin'})
                .then(r => { if (r.status === 401) { window.location = '/login'; return; } return r.json(); })
                .then(data => { if (data) applyFlags(data); });
        }
        function toggleWebLogs() {
            fetch('/set_web_logs?value=' + (window._webLogs ? 0 : 1), {method: 'POST', credentials: 'same-origin'})
                .then(r => { if (r.status === 401) { window.location = '/login'; return; } return r.json(); })
                .then(data => { if (data) applyFlags(data); });
        }
        function togglePause() {
            window._paused = !window._paused;
            if (pauseBtn) {
                pauseBtn.textContent = window._paused ? "RESUME" : "PAUSE";
                pauseBtn.className = window._paused ? "debug-on" : "debug-off";
            }
            if (!window._paused) refresh();
        }
        function applyFlags(data) {
            window._debug = !!data.debug_mode;
            window._webLogs = !!data.web_logs;
            if (debugBtn) {
                debugBtn.textContent = "DEBUG: " + (data.debug_mode ? "ON" : "OFF");
                debugBtn.className = data.debug_mode ? "debug-on" : "debug-off";
            }
            if (webLogBtn) {
                webLogBtn.textContent = "WEB LOGS: " + (data.web_logs ? "ON" : "OFF");
                webLogBtn.className = data.web_logs ? "debug-on" : "debug-off";
            }
        }
        function refresh() {
            fetch('/logs.json', {credentials: 'same-origin'})
                .then(r => {
                    if (r.status === 401) { window.location = '/login'; return; }
                    return r.json();
                })
                .then(data => {
                    if (!data) return;
                    applyFlags(data);
                    if (window._paused) {
                        document.getElementById("meta").textContent = "PAUSED — display frozen";
                        return;
                    }
                    document.getElementById("meta").textContent = data.web_logs
                        ? (data.count + " lines (newest at bottom)")
                        : "Web log capture is OFF";
                    pre.textContent = data.web_logs
                        ? data.lines.join("\\n")
                        : "(enable WEB LOGS to capture here — launch terminal still gets everything)";
                    if (data.web_logs) pre.scrollTop = pre.scrollHeight;
                });
        }
        setInterval(refresh, 2000);
        refresh();
    </script>
</body>
</html>
"""

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module cannot be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py")
    exit(0)
#----------------------------------------------------------#
