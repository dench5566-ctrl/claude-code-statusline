#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code status line: model, context tokens, cost, rate limits.

Claude reports used_percentage (how much has been spent). This script inverts
that to remaining quota: bars start full at 100% and drain to 0%. Color still
tracks pressure (spent), so a nearly empty bar turns orange then red.
"""
import json
import os
import subprocess
import sys
import time

# Label language: "en" or "ru".
LOCALE = "en"

LABELS = {
    "en": {
        "five_hour": "5h", "seven_day": "week", "spend_limit": "spend",
        "hour": "h", "min": "m", "sec": "s", "day": "d",
        "no_limits": "limits: no data yet (they arrive with the first response)",
    },
    "ru": {
        "five_hour": "5\u0447", "seven_day": "\u043d\u0435\u0434", "spend_limit": "$\u043b\u0438\u043c",
        "hour": "\u0447", "min": "\u043c", "sec": "\u0441", "day": "\u0434",
        "no_limits": "\u043b\u0438\u043c\u0438\u0442\u044b: \u043d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445 (\u043f\u043e\u044f\u0432\u044f\u0442\u0441\u044f \u043f\u043e\u0441\u043b\u0435 \u043f\u0435\u0440\u0432\u043e\u0433\u043e \u043e\u0442\u0432\u0435\u0442\u0430)",
    },
}
L = LABELS.get(LOCALE, LABELS["en"])

R = "\033[0m"


def c(code, s):
    return "\033[38;5;%dm%s%s" % (code, s, R)


GREY = 245
DIM = 249
BLUE = 32
TEAL = 37
PURPLE = 97
ORANGE = 172
RED = 160
INK = 240


def load():
    try:
        return json.loads(sys.stdin.read() or "{}")
    except Exception:
        return {}


def num(n):
    n = int(n or 0)
    for div, suf in ((1_000_000, "M"), (1_000, "k")):
        if n >= div:
            v = n / float(div)
            return ("%d%s" if v >= 100 or v == int(v) else "%.1f%s") % (v, suf)
    return str(n)


def heat(used_pct):
    """Color by pressure (spent), not by remaining fill."""
    if used_pct >= 90:
        return RED
    if used_pct >= 70:
        return ORANGE
    if used_pct >= 40:
        return TEAL
    return BLUE


def bar(remaining_pct, used_pct, width=10):
    remaining_pct = max(0.0, min(100.0, float(remaining_pct)))
    filled = int(round(remaining_pct / 100.0 * width))
    return c(heat(used_pct), "▰" * filled) + c(DIM, "▱" * (width - filled))


def until(ts):
    """Human 'resets in' for a unix-seconds timestamp."""
    if not ts:
        return None
    left = int(ts) - int(time.time())
    if left <= 0:
        return "0" + L["min"]
    h, m = left // 3600, (left % 3600) // 60
    if h >= 24:
        return "%d%s %d%s" % (h // 24, L["day"], h % 24, L["hour"])
    if h:
        return "%d%s %02d%s" % (h, L["hour"], m, L["min"])
    return "%d%s" % (max(m, 1), L["min"])


def branch(cwd):
    try:
        out = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=0.4,
        )
        if out.returncode != 0:
            return None
        name = out.stdout.strip()
        if not name:
            return None
        dirty = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain", "--untracked-files=no"],
            capture_output=True, text=True, timeout=0.4,
        )
        return name + ("*" if dirty.stdout.strip() else "")
    except Exception:
        return None


def remaining(used_pct, remaining_pct=None):
    used_pct = float(used_pct or 0)
    if remaining_pct is not None:
        return used_pct, float(remaining_pct)
    return used_pct, max(0.0, 100.0 - used_pct)


def main():
    d = load()
    cwd = (d.get("workspace") or {}).get("current_dir") or d.get("cwd") or os.getcwd()

    # ---------- line 1 ----------
    row = []

    model = (d.get("model") or {}).get("display_name") or "?"
    eff = (d.get("effort") or {}).get("level")
    tag = model + ("·" + eff if eff else "")
    if d.get("fast_mode"):
        tag += " ⚡"
    if (d.get("thinking") or {}).get("enabled") is False:
        tag += " \U0001f4a4"
    row.append(c(PURPLE, "◆ " + tag))

    home = os.path.expanduser("~")
    short = "~" + cwd[len(home):] if cwd.startswith(home) else cwd
    short = os.path.basename(short.rstrip("/")) or short
    br = branch(cwd)
    row.append(c(BLUE, short) + (c(GREY, " (" + br + ")") if br else ""))

    ctx = d.get("context_window") or {}
    used = ctx.get("total_input_tokens") or 0
    size = ctx.get("context_window_size") or 0
    if size:
        used_pct, left_pct = remaining(
            ctx.get("used_percentage") or (used * 100.0 / size),
            ctx.get("remaining_percentage"),
        )
        left = max(int(size) - int(used), 0)
        row.append(
            c(GREY, "ctx ")
            + c(heat(used_pct), "%s/%s" % (num(left), num(size)))
            + c(heat(used_pct), " %d%%" % round(left_pct))
        )
        out_tok = ctx.get("total_output_tokens") or 0
        if out_tok:
            row.append(c(GREY, "out " + num(out_tok)))

    cost = (d.get("cost") or {}).get("total_cost_usd")
    if cost:
        row.append(c(INK, "$%.2f" % cost))

    dur = (d.get("cost") or {}).get("total_duration_ms")
    if dur:
        row.append(c(GREY, "%d%s" % (dur / 60000, L["min"]) if dur >= 60000
                     else "%d%s" % (dur / 1000, L["sec"])))

    lines = [c(DIM, " │ ").join(row)]

    # ---------- line 2: rate limits (remaining quota) ----------
    rl = d.get("rate_limits") or {}
    seg = []
    for key in ("five_hour", "seven_day", "spend_limit"):
        w = rl.get(key)
        if not w:
            continue
        used_pct, left_pct = remaining(w.get("used_percentage") or 0)
        reset = until(w.get("resets_at"))
        seg.append(
            c(GREY, L[key] + " ")
            + bar(left_pct, used_pct)
            + c(heat(used_pct), " %d%%" % round(left_pct))
            + (c(DIM, " ↺" + reset) if reset else "")
        )
    if seg:
        lines.append(c(DIM, "  ").join(seg))
    else:
        lines.append(c(DIM, L["no_limits"]))

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
