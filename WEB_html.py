#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  WEB_html.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

from   WEB_shared_css import SHARED_CSS

HTML = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Info Center</title>
    <style>
""" + SHARED_CSS + """
    </style>
</head>
<body>
    <h1>Info Center</h1>
    <div class="status" id="status">Loading...</div>

    <div class="grid-2x3">
        <button class="power-off" onclick="call('/power_off')">POWER<br>OFF</button>
        <button class="power-on"  onclick="call('/power_on')">POWER<br>ON</button>
    </div>

    <label>Brightness</label>
    <input type="range" id="bright" min="8" max="255" step="8">

    <button id="autoBtn" class="auto-off" onclick="toggleAuto()">AUTO BRIGHT: --</button>
    <div class="note" id="autoNote"></div>

    <div class="grid-2x3">
        <button id="setDayBtn" class="pattern" onclick="setDayBright()">SET DAY<br>--</button>
        <button id="setNightBtn" class="pattern" onclick="setNightBright()">SET NIGHT<br>--</button>
    </div>

    <button id="militaryBtn" class="debug-off" onclick="toggleMilitary()">MILITARY TIME: --</button>
    <button id="tempUnitBtn" class="debug-off" onclick="toggleTempUnit()">TEMP: --</button>
    <button id="globePushBtn" class="debug-off" onclick="toggleGlobePush()">PUSH GLOBE: OFF</button>

    <label>PRIMARY</label>
    <input id="fxPrimary" maxlength="3" autocomplete="off"
           style="text-transform:uppercase;width:4em">
    <br>
    <button class="pattern" onclick="setFxPrimary()">SET PRIMARY CURRENCY</button>

    <label>SECONDARY</label>
    <input id="fxSecondary" maxlength="3" autocomplete="off"
           style="text-transform:uppercase;width:4em">
    <br>
    <button class="pattern" onclick="setFxSecondary()">SET SECONDARY CURRENCY</button>
    <div class="note">for exchange rate only</div>

    <br>
    {% if role == "tech" %}
    <button class="nav-btn" onclick="window.location='/diag'">TECH</button>
    {% endif %}
        
    <br>
    <button class="logout" onclick="logout()">Logout</button>

    <script>
        let sliding = false;
        window._autoBright = false;
        window._military = false;
        window._tempC = true;
        window._globePush = false;
        const slider = document.getElementById("bright");
        const autoBtn = document.getElementById("autoBtn");
        const autoNote = document.getElementById("autoNote");
        const setDayBtn = document.getElementById("setDayBtn");
        const setNightBtn = document.getElementById("setNightBtn");
        const militaryBtn = document.getElementById("militaryBtn");
        const tempUnitBtn = document.getElementById("tempUnitBtn");
        const globePushBtn = document.getElementById("globePushBtn");
        const fxPrimary = document.getElementById("fxPrimary");
        const fxSecondary = document.getElementById("fxSecondary");

        function toggleGlobePush() {
            call('/set_globe_push?value=' + (window._globePush ? 0 : 1));
        }
        function normCcy(raw, fallback) {
            const s = String(raw || "").toUpperCase().replace(/[^A-Z]/g, "").slice(0, 3);
            return s || fallback;
        }
        function setFxPrimary() {
            const p = normCcy(fxPrimary && fxPrimary.value, "USD");
            if (fxPrimary) { fxPrimary.value = p; fxPrimary.style.color = ""; }
            call('/set_exchange_pair?primary=' + encodeURIComponent(p));
        }
        function setFxSecondary() {
            const s = normCcy(fxSecondary && fxSecondary.value, "PHP");
            if (fxSecondary) { fxSecondary.value = s; fxSecondary.style.color = ""; }
            call('/set_exchange_pair?secondary=' + encodeURIComponent(s));
        }
        if (fxPrimary) {
            fxPrimary.addEventListener("input", () => { fxPrimary.style.color = ""; });
        }
        if (fxSecondary) {
            fxSecondary.addEventListener("input", () => { fxSecondary.style.color = ""; });
        }
        slider.addEventListener("mousedown",  () => sliding = true);
        slider.addEventListener("touchstart", () => sliding = true);
        slider.addEventListener("mouseup", () => { sliding = false; setBrightness(slider.value); });
        slider.addEventListener("touchend", () => { sliding = false; setBrightness(slider.value); });
        slider.addEventListener("change", () => setBrightness(slider.value));

        function call(url, method) {
            fetch(url, {method: method || "POST", credentials: "same-origin"})
                .then(r => {
                    if (r.status === 401) { window.location = "/login"; return; }
                    return r.json();
                })
                .then(data => { if (data) updateStatus(data); })
                .catch(err => console.log(err));
        }
        function setBrightness(val) {
            fetch('/set_brightness?value=' + val, {method: 'POST', credentials: 'same-origin'})
                .then(r => {
                    if (r.status === 401) { window.location = '/login'; return; }
                    return r.json();
                })
                .then(data => { if (data) updateStatus(data); });
        }
        function setDayBright() { call('/set_day_brightness?value=' + slider.value); }
        function setNightBright() { call('/set_night_brightness?value=' + slider.value); }
        function toggleAuto() { call('/set_auto_brightness?value=' + (window._autoBright ? 0 : 1)); }
        function toggleMilitary() { call('/set_military_time?value=' + (window._military ? 0 : 1)); }
        function toggleTempUnit() { call('/set_temp_celsius?value=' + (window._tempC ? 0 : 1)); }
        function logout() {
            fetch('/logout', {credentials: 'same-origin'})
                .then(() => window.location = '/login');
        }
        function updateStatus(data) {
            let powerText = "ON";
            let cls = "";
            if (data.power_level === 1) { powerText = "BLACKOUT"; cls = "status-warn"; }
            else if (data.power_level === 2) { powerText = "BLACKOUT + QUIET MODE"; cls = "status-warn"; }
            window._autoBright = !!data.auto_brightness;
            window._military = !!data.military_time;
            window._tempC = data.temp_celsius !== false;
            document.getElementById("status").className = "status " + cls;
            document.getElementById("status").innerHTML =
                "Brightness: <b>" + data.brightness + "</b><br>" +
                "Auto bright: <b>" + (data.auto_brightness ? "YES" : "NO") + "</b><br>" +
                "Day / Night: <b>" + data.day_brightness + " / " + data.night_brightness + "</b><br>" +
                "Military: <b>" + (data.military_time ? "ON" : "OFF") + "</b><br>" +
                "Temp: <b>" + (window._tempC ? "C" : "F") + "</b><br>" +
                "Power: <b>" + powerText + "</b><br>" +
                "Internet: <b style='color:" + data.internet_color + "'>" + data.internet + "</b><br>" +
                "Globe: <b style='color:" + data.globe_color + "'>" + data.globe + "</b>";
            window._globePush = !!data.globe_push;
            if (globePushBtn) {
                globePushBtn.textContent = "PUSH GLOBE: " + (data.globe_push ? "ON" : "OFF");
                globePushBtn.className = data.globe_push ? "debug-on" : "debug-off";
            }
            if (autoBtn) {
                autoBtn.textContent = "AUTO BRIGHT: " + (data.auto_brightness ? "YES" : "NO");
                autoBtn.className = data.auto_brightness ? "auto-on" : "auto-off";
            }
            if (autoNote) {
                autoNote.textContent = data.auto_brightness ? "" : "Manual brightness – auto disabled";
            }
            if (setDayBtn) {
                setDayBtn.innerHTML = "SET DAY<br>" + data.day_brightness;
            }
            if (setNightBtn) {
                setNightBtn.innerHTML = "SET NIGHT<br>" + data.night_brightness;
            }
            if (militaryBtn) {
                militaryBtn.textContent = "MILITARY TIME: " + (data.military_time ? "ON" : "OFF");
                militaryBtn.className = data.military_time ? "debug-on" : "debug-off";
            }
            if (tempUnitBtn) {
                tempUnitBtn.textContent = "TEMP: " + (window._tempC ? "C" : "F");
                tempUnitBtn.className = window._tempC ? "debug-on" : "debug-off";
            }
            if (fxPrimary && document.activeElement !== fxPrimary) {
                fxPrimary.value = data.exchange_primary || data.exchange_base || "USD";
                fxPrimary.style.color = (data.primary_valid === false) ? "#f00" : "#0c0";
            }
            if (fxSecondary && document.activeElement !== fxSecondary) {
                fxSecondary.value = data.exchange_secondary || data.exchange_quote || "PHP";
                fxSecondary.style.color = (data.secondary_valid === false) ? "#f00" : "#0c0";
            }
            if (!sliding) slider.value = data.brightness;
        }
        setInterval(() => call("/status", "GET"), 2000);
        call("/status", "GET");
    </script>
</body>
</html>
"""
