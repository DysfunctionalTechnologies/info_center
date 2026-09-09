#----------------------------------------------------------#
#----------------------------------------------------------#
# Project: Info_Center_16x32
# Module:  WEB_shared_css.py
# Author:  Timothy S. Carlson - with Grok AI's assistance
#----------------------------------------------------------#
#----------------------------------------------------------#

SHARED_CSS = """
    body {
        font-family: system-ui, sans-serif;
        background: #111;
        color: #eee;
        text-align: center;
        padding: 16px;
        max-width: 420px;
        margin: 0 auto;
    }
    h1 { margin: 0 0 8px 0; font-size: 1.6em; }
    .status {
        background: #222;
        padding: 12px;
        border-radius: 10px;
        margin-bottom: 20px;
        font-size: 1.1em;
        line-height: 1.5;
    }
    .status-warn { color: #f80; }
    button, input[type=range] {
        font-size: 1.15em;
        margin: 6px 0;
        width: 100%;
        max-width: 340px;
    }
    button {
        padding: 14px;
        border: none;
        border-radius: 12px;
        background: #333;
        color: white;
    }
    button:active { background: #555; }
    .power-on  { background: #0a0; }
    .power-off { background: #a00; }
    .pattern   { background: #246; }
    .alert-btn { background: #842; }
    .alert-on  { background: #c40; }
    .refresh-ready { background: #0a0; }
    .refresh-cooldown { background: #a00; }
    .auto-on   { background: #0a0; }
    .auto-off  { background: #a00; }
    .debug-on  { background: #0a0; }
    .debug-off { background: #a00; }
    .nav-btn   { background: #468; }
    .logout    { background: #444; margin-top: 28px; }
    label { display: block; margin-top: 16px; margin-bottom: 4px; }
    .note { color: #f80; margin-top: 8px; min-height: 1.2em; font-size: 0.95em; }
    .note:empty { display: none; margin: 0; }
    .section {
        margin-top: 22px;
        margin-bottom: 8px;
        font-size: 0.95em;
        color: #aaa;
    }
    .grid-2x3 {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 8px;
        max-width: 340px;
        margin: 0 auto 16px auto;
    }
    .grid-2x3 button {
        margin: 0;
        padding: 12px 8px;
        line-height: 1.25;
        font-size: 1.05em;
    }
    pre.logbox {
        text-align: left;
        background: #000;
        color: #8f8;
        font-size: 0.72em;
        line-height: 1.35;
        padding: 10px;
        border-radius: 10px;
        height: 52vh;
        overflow: auto;
        white-space: pre-wrap;
        word-break: break-word;
    }
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
