#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Version: V1.19
# Date:    September 2, 2026
# Module:  WEB_diag.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

from   WEB_shared_css import SHARED_CSS

HTML_DIAG = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Info Center – Tech</title>
    <style>
""" + SHARED_CSS + """
    </style>
</head>
<body>
    <h1>TECH</h1>
    <div class="status" id="status">Loading...</div>

    <button id="refreshBtn" class="refresh-ready" onclick="call('/force_refresh')">Force Refresh Data</button>

    <div class="section">Hardware tests</div>
    <div class="grid-2x3">
        <button class="pattern" onclick="call('/diag_test/1')">1 PANEL<br>DIAGNOSTIC</button>
        <button class="pattern" onclick="call('/diag_test/2')">2<br>INDICATORS</button>
        <button class="pattern" onclick="call('/diag_test/3')">3 FONT<br>CHARS</button>
        <button class="pattern" onclick="call('/diag_test/4')">4 TEMP<br>SENSOR</button>
        <button class="pattern" onclick="call('/diag_test/5')">5 WEBSITE<br>PINGS</button>
    </div>

    <div class="section">Force Pattern</div>
    <div class="grid-2x3">
        <button class="pattern" onclick="call('/force/6')">INTERNET<br>MONITOR</button>
        <button class="pattern" onclick="call('/force/7')">PACMAN</button>
        <button class="pattern" onclick="call('/force/8')">WEATHER</button>
        <button class="pattern" onclick="call('/force/9')">EXCHANGE<br>RATE</button>
        <button class="pattern" onclick="call('/force/10')">CRUDE<br>OIL</button>
        <button class="pattern" onclick="call('/force/11')">EARTHQUAKE</button>
    </div>

    <div class="section">Alert Testing</div>
    <button class="alert-btn" onclick="call('/alert/reset')">RESET<br>ALL ALERTS</button>
    <div class="grid-2x3">
        <button id="alertThunderBtn" class="alert-btn" onclick="call('/alert/thunder')">THUNDER<br>(YELLOW)</button>
        <button id="alertHeavyBtn" class="alert-btn" onclick="call('/alert/heavy')">HEAVY RAIN<br>(RED)</button>
        <button id="alertQuakeYBtn" class="alert-btn" onclick="call('/alert/quake_yellow')">QUAKE (5.0-5.9)<br>(YELLOW)</button>
        <button id="alertQuakeRBtn" class="alert-btn" onclick="call('/alert/quake_red')">QUAKE (6.0 PLUS)<br>(RED)</button>
    </div>

    <div class="section">Platform (this Pi)</div>
    <p class="muted">{{ plat_path }}<br>
    {% if plat_present %}file present{% else %}missing — using defaults{% endif %}</p>
    <form method="post" action="/platform_save">
        <label>Name <input name="DISPLAY_NAME" value="{{ plat.DISPLAY_NAME }}"></label><br>
        <label>Layout
            <select name="PANEL_LAYOUT">
                <option value="16x16" {% if plat.PANEL_LAYOUT == "16x16" %}selected{% endif %}>16x16</option>
                <option value="8x32" {% if plat.PANEL_LAYOUT == "8x32" %}selected{% endif %}>8x32 stacked</option>
            </select>
        </label><br>
        <label>GPIO <input name="GPIO_PIN" type="number" min="0" max="27" value="{{ plat.GPIO_PIN }}"></label><br>
        <label><input type="checkbox" name="GLOBE_PUSH" value="1" {% if plat.GLOBE_PUSH == "1" %}checked{% endif %}> Globe push</label><br>
        <label>Globe host <input name="GLOBE_HOST" value="{{ plat.GLOBE_HOST }}"></label><br>
        <button type="submit">Save</button>
        <button type="submit" formaction="/platform_save_reboot" name="confirm" value="REBOOT"
                onclick="return confirm('Save and reboot this Pi?');">Save and reboot</button>
    </form>

    <br>
    <button class="nav-btn" onclick="window.location='/'">← Back to Controls</button>
    <button class="nav-btn" onclick="window.location='/logs'">Logs</button>
    <button class="logout" onclick="logout()">Logout</button>

    <script>
        const refreshBtn = document.getElementById("refreshBtn");
        function call(url, method) {
            fetch(url, {method: method || 'POST', credentials: 'same-origin'})
                .then(r => {
                    if (r.status === 401) { window.location = '/login'; return; }
                    return r.json();
                })
                .then(data => { if (data) updateStatus(data); })
                .catch(err => console.log(err));
        }
        function logout() {
            fetch('/logout', {credentials: 'same-origin'})
                .then(() => window.location = '/login');
        }
        function paintAlertBtn(el, on, onHtml, offHtml) {
            if (!el) return;
            el.innerHTML = on ? onHtml : offHtml;
            el.className = on ? 'alert-on' : 'alert-btn';
        }
        function updateStatus(data) {
            let powerText = 'ON';
            let cls = '';
            if (data.power_level === 1) { powerText = 'BLACKOUT'; cls = 'status-warn'; }
            else if (data.power_level === 2) { powerText = 'BLACKOUT + QUIET MODE'; cls = 'status-warn'; }
            document.getElementById('status').className = 'status ' + cls;
            document.getElementById('status').innerHTML =
                'Brightness: <b>' + data.brightness + '</b><br>' +
                'Auto bright: <b>' + (data.auto_brightness ? 'YES' : 'NO') + '</b><br>' +
                'Day / Night: <b>' + data.day_brightness + ' / ' + data.night_brightness + '</b><br>' +
                'Military: <b>' + (data.military_time ? 'ON' : 'OFF') + '</b><br>' +
                'Temp: <b>' + (data.temp_celsius !== false ? 'C' : 'F') + '</b><br>' +
                'Debug: <b>' + (data.debug_mode ? 'ON' : 'OFF') + '</b><br>' +
                'Web logs: <b>' + (data.web_logs ? 'ON' : 'OFF') + '</b><br>' +
                'Power: <b>' + powerText + '</b><br>' +
                'Internet: <b style="color:' + data.internet_color + '">' + data.internet + '</b><br>' +
                'Globe: <b style="color:' + data.globe_color + '">' + data.globe + '</b>';
            paintAlertBtn(document.getElementById('alertThunderBtn'),
                !!data.alert_thunder, 'THUNDER<br>(YELLOW) ON', 'THUNDER<br>(YELLOW)');
            paintAlertBtn(document.getElementById('alertHeavyBtn'),
                !!data.alert_heavy, 'HEAVY RAIN<br>(RED) ON', 'HEAVY RAIN<br>(RED)');
            paintAlertBtn(document.getElementById('alertQuakeYBtn'),
                !!data.alert_quake_yellow, 'QUAKE (5.0-5.9)<br>(YELLOW) ON', 'QUAKE (5.0-5.9)<br>(YELLOW)');
            paintAlertBtn(document.getElementById('alertQuakeRBtn'),
                !!data.alert_quake_red, 'QUAKE (6.0 PLUS)<br>(RED) ON', 'QUAKE (6.0 PLUS)<br>(RED)');
            if (refreshBtn) {
                if (data.refreshing) {
                    refreshBtn.className = 'refresh-cooldown';
                    refreshBtn.textContent = 'Refreshing…';
                } else if (data.refresh_cooldown > 0) {
                    refreshBtn.className = 'refresh-cooldown';
                    refreshBtn.textContent = 'Refresh in ' + data.refresh_cooldown + 's';
                } else {
                    refreshBtn.className = 'refresh-ready';
                    refreshBtn.textContent = 'Force Refresh Data';
                }
            }
        }
        setInterval(() => call('/status', 'GET'), 2000);
        call('/status', 'GET');
    </script>
</body>
</html>
"""
