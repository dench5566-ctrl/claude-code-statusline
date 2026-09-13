#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Claude Code status line: model, context tokens, cost, rate limits."""
import json
import os
import subprocess
import sys
import time

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


def heat(pct):
    if pct >= 90:
        return RED
    if pct >= 70:
        return ORANGE
    if pct >= 40:
        return TEAL
    return BLUE


def bar(pct, width=10):
    pct = max(0.0, min(100.0, float(pct)))
    filled = int(round(pct / 100.0 * width))
    return c(heat(pct), "▰" * filled) + c(DIM, "▱" * (width - filled))


def until(ts):
    """Human 'resets in' for a unix-seconds timestamp."""
    if not ts:
        return None
    left = int(ts) - int(time.time())
    if left <= 0:
        return "сейчас"
    h, m = left // 3600, (left % 3600) // 60
    if h >= 24:
        d = h // 24
        return "%dд %dч" % (d, h % 24)
    if h:
        return "%dч %02dм" % (h, m)
    return "%dм" % max(m, 1)


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
    row.append(c(BLUE, short) + (c(GREY, " ⎇ " + br) if br else ""))

    ctx = d.get("context_window") or {}
    used = ctx.get("total_input_tokens") or 0
    size = ctx.get("context_window_size") or 0
    if size:
        pct = float(ctx.get("used_percentage") or (used * 100.0 / size))
        row.append(
            c(GREY, "ctx ")
            + c(heat(pct), "%s/%s" % (num(used), num(size)))
            + c(heat(pct), " %d%%" % round(pct))
        )
        out_tok = ctx.get("total_output_tokens") or 0
        if out_tok:
            row.append(c(GREY, "out " + num(out_tok)))

    cost = (d.get("cost") or {}).get("total_cost_usd")
    if cost:
        row.append(c(INK, "$%.2f" % cost))

    dur = (d.get("cost") or {}).get("total_duration_ms")
    if dur:
        row.append(c(GREY, "%dм" % (dur / 60000) if dur >= 60000 else "%dс" % (dur / 1000)))

    lines = [c(DIM, " │ ").join(row)]

    # ---------- line 2: rate limits ----------
    rl = d.get("rate_limits") or {}
    seg = []
    for key, label in (("five_hour", "5ч"), ("seven_day", "нед"), ("spend_limit", "$лим")):
        w = rl.get(key)
        if not w:
            continue
        pct = float(w.get("used_percentage") or 0)
        left = until(w.get("resets_at"))
        seg.append(
            c(GREY, label + " ")
            + bar(pct)
            + c(heat(pct), " %d%%" % round(pct))
            + (c(DIM, " ↺" + left) if left else "")
        )
    if seg:
        lines.append(c(DIM, "  ").join(seg))
    else:
        lines.append(c(DIM, "лимиты: нет данных (появятся после первого ответа)"))

    sys.stdout.write("\n".join(lines))


if __name__ == "__main__":
    main()
