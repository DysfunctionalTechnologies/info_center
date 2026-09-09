#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  WEB_login.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

HTML_LOGIN = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Info Center Login</title>
    <style>
        body { font-family: system-ui, sans-serif; background:#111; color:#eee;
               text-align:center; padding:40px 16px; max-width:420px; margin:0 auto; }
        h1 { margin-bottom:24px; }
        .field { position: relative; max-width: 300px; margin: 12px auto; }
        input { font-size:1.2em; padding:12px 44px 12px 12px; width:100%;
                border-radius:8px; border:none; box-sizing: border-box; }
        .eye {
            position: absolute; right: 10px; top: 50%; transform: translateY(-50%);
            background: none; border: none; color: #aaa;
            cursor: pointer; padding: 4px; line-height: 0;
        }
        button.submit { font-size:1.2em; padding:14px 32px; margin-top:20px;
                 background:#0a0; color:white; border:none; border-radius:12px; width: 100%; max-width: 300px; }
        .error { color:#f44; margin-top:16px; }
    </style>
</head>
<body>
    <h1>Info Center</h1>
    <form method="POST">
        <div class="field">
            <input type="text" name="username" placeholder="Username" required autofocus>
        </div>
        <div class="field">
            <input type="password" name="password" id="pwd" placeholder="Password" required>
            <button type="button" class="eye" id="eyeBtn" onclick="togglePwd()"
                    title="Show password" aria-label="Show password">
                <svg width="22" height="22" viewBox="0 0 24 24" fill="none"
                     stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 3l18 18"/>
                    <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/>
                    <path d="M9.9 5.1A9.8 9.8 0 0 1 12 5c5 0 9 4 10 7-0.4 1.1-1.2 2.4-2.3 3.6"/>
                    <path d="M6.1 6.1C4.2 7.6 2.7 9.6 2 12c1 3 5 7 10 7 1.8 0 3.5-0.5 5-1.4"/>
                </svg>
            </button>
        </div>
        <button type="submit" class="submit">Login</button>
    </form>
    {% if error %}<div class="error">{{ error }}</div>{% endif %}
    <script>
        const EYE_CLOSED = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none"
            stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M3 3l18 18"/>
            <path d="M10.6 10.6a2 2 0 0 0 2.8 2.8"/>
            <path d="M9.9 5.1A9.8 9.8 0 0 1 12 5c5 0 9 4 10 7-0.4 1.1-1.2 2.4-2.3 3.6"/>
            <path d="M6.1 6.1C4.2 7.6 2.7 9.6 2 12c1 3 5 7 10 7 1.8 0 3.5-0.5 5-1.4"/>
        </svg>`;
        const EYE_OPEN = `<svg width="22" height="22" viewBox="0 0 24 24" fill="none"
            stroke="#aaa" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/>
            <circle cx="12" cy="12" r="3"/>
        </svg>`;
        function togglePwd() {
            const p = document.getElementById("pwd");
            const btn = document.getElementById("eyeBtn");
            const show = (p.type === "password");
            p.type = show ? "text" : "password";
            btn.innerHTML = show ? EYE_OPEN : EYE_CLOSED;
            btn.title = show ? "Hide password" : "Show password";
            btn.setAttribute("aria-label", btn.title);
        }
    </script>
</body>
</html>
"""

#----------------------------------------------------------#
if __name__ == "__main__":
#----------------------------------------------------------#
    print("This module should not be run directly.")
    print("Please run either INFO_CENTER.py or DIAGNOSTICS.py\n")
    from INFO_CENTER import main
    main()
    exit(0)
#----------------------------------------------------------#
