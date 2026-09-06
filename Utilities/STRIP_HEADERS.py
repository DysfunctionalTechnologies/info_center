#!/usr/bin/env python3
"""Strip mid-file #------# banners. Keeps file header + __main__ footer."""
import pathlib
import re
import sys

DASH = re.compile(r"^#-{8,}#\s*$")
BOX_TITLE = re.compile(r"^#\s+.+\s*#\s*$")  # unused; we only drop pure dash lines

KEEP_NAMES = {
    "CONFIG.py", "DATA_FETCHER.py", "DIAGNOSTICS.py", "DISPLAY.py",
    "EARTHQUAKE.py", "EEPROM.py", "EXCHANGE.py", "FONT_3X6.py",
    "GLOBE_LINK.py", "IMONITOR.py", "INDICATORS.py", "INFO_CENTER.py",
    "OIL.py", "PACMAN.py", "PANEL.py", "RPI_WS281X.py",
    "TEMPERATURE.py", "WEATHER.py", "WEB.py",
}

def is_dash(line: str) -> bool:
    return bool(DASH.match(line.rstrip("\n")))

def strip_text(text: str) -> str:
    lines = text.splitlines(keepends=True)
    n = len(lines)

    # --- header: from start through the closing dash pair after Author ---
    i = 0
    header_end = 0
    dash_run = 0
    seen_project = False
    while i < n:
        raw = lines[i]
        if is_dash(raw):
            dash_run += 1
        else:
            if "Project:" in raw:
                seen_project = True
            dash_run = 0
        i += 1
        if seen_project and dash_run >= 2:
            header_end = i
            break

    # --- footer: last `if __name__` through EOF ---
    footer_start = n
    for j in range(n - 1, -1, -1):
        if lines[j].lstrip().startswith("if __name__"):
            # include preceding dash banner
            k = j
            while k > 0 and is_dash(lines[k - 1]):
                k -= 1
            footer_start = k
            break

    def keep_mid(line: str) -> bool:
        return not is_dash(line)

    out = []
    out.extend(lines[:header_end])
    mid = [ln for ln in lines[header_end:footer_start] if keep_mid(ln)]
    # collapse 3+ blank lines to 2
    cleaned = []
    blanks = 0
    for ln in mid:
        if ln.strip() == "":
            blanks += 1
            if blanks <= 2:
                cleaned.append(ln if ln.endswith("\n") else ln + "\n")
        else:
            blanks = 0
            cleaned.append(ln if ln.endswith("\n") else ln + "\n")
    out.extend(cleaned)
    out.extend(lines[footer_start:])
    return "".join(out)

def main():
    root = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    for path in sorted(root.glob("*.py")):
        if path.name not in KEEP_NAMES:
            continue
        original = path.read_text(encoding="utf-8")
        updated = strip_text(original)
        if updated != original:
            path.write_text(updated, encoding="utf-8")
            print(f"updated {path.name}")
        else:
            print(f"unchanged {path.name}")

if __name__ == "__main__":
    main()
