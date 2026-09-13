# claude-code-statusline

A single-file status line for [Claude Code](https://code.claude.com) that shows what
actually matters while you work: the model, context window usage, session cost, and —
the part most status lines miss — your **subscription rate limits** (5-hour and weekly
windows) with time until reset.

```
◆ Opus 5·high ⚡ │ my-project ⎇ main* │ ctx 152k/200k 76% │ out 18.2k │ $0.42 │ 7м
5ч ▰▰▰▰▰▰▰▰▰▱ 94% ↺25м   нед ▰▱▱▱▱▱▱▱▱▱ 12% ↺5д 18ч
```

No dependencies beyond the Python 3 that ships with macOS and most Linux distros.

## What it shows

**Line 1**

| Segment | Meaning |
| --- | --- |
| `◆ Opus 5·high` | Active model and effort level |
| `⚡` / `💤` | Fast mode on / extended thinking off |
| `my-project ⎇ main*` | Current directory and git branch (`*` = uncommitted changes) |
| `ctx 152k/200k 76%` | Context window: tokens used, window size, percentage |
| `out 18.2k` | Output tokens generated this session |
| `$0.42` | Session cost |
| `7м` | Wall-clock session duration |

**Line 2 — rate limits**

Subscription plans report a 5-hour window (`5ч`) and a weekly window (`нед`), each with a
bar, a percentage, and time until reset (`↺`). API/gateway accounts get a spend limit
(`$лим`) instead. Before the first model response of a session the data isn't available
yet, and the line says so.

Colors track pressure: blue → teal → orange at 70% → red at 90%. The palette is picked to
stay readable on light terminals and to remain distinguishable for colorblind users
(it avoids relying on a red/green contrast).

## Install

```sh
curl -fsSL https://raw.githubusercontent.com/dench5566-ctrl/claude-code-statusline/main/statusline.py \
  -o ~/.claude/statusline.py
```

Then add this to `~/.claude/settings.json`:

```json
{
  "statusLine": {
    "type": "command",
    "command": "/usr/bin/python3 ~/.claude/statusline.py",
    "padding": 0,
    "refreshInterval": 10
  }
}
```

Restart `claude` if the line doesn't appear immediately.

On Linux, point the command at your interpreter (`python3` on `PATH` usually works);
on Windows use `python C:\Users\<you>\.claude\statusline.py`.

## Requirements

- Claude Code **2.1.x** or newer — earlier versions don't pass `context_window` or
  `rate_limits` to the status line, and those segments will silently be omitted.
- Python 3.8+
- A terminal with 256-color support

## How it works

Claude Code runs the status line command on every render and pipes a JSON payload to
stdin. The script reads that payload and prints two lines. The fields it uses:

```jsonc
{
  "model":          { "display_name": "Opus 5" },
  "effort":         { "level": "high" },
  "fast_mode":      false,
  "thinking":       { "enabled": true },
  "workspace":      { "current_dir": "/path/to/project" },
  "context_window": { "total_input_tokens": 0, "total_output_tokens": 0,
                      "context_window_size": 200000, "used_percentage": 0 },
  "cost":           { "total_cost_usd": 0.0, "total_duration_ms": 0 },
  "rate_limits":    { "five_hour":   { "used_percentage": 0, "resets_at": 0 },
                      "seven_day":   { "used_percentage": 0, "resets_at": 0 },
                      "spend_limit": { "used_percentage": 0, "resets_at": 0 } }
}
```

Every field is optional in practice — a missing one drops its segment rather than
breaking the line, so the script degrades gracefully across versions and account types.

Git branch detection shells out to `git` with a 0.4s timeout and is skipped outside a
repository.

## Customizing

Everything worth tweaking sits at the top of the file:

- `GREY`, `BLUE`, `TEAL`, `ORANGE`, `RED`, … — 256-color codes
- `heat()` — the thresholds where colors escalate (40 / 70 / 90 percent)
- `bar(pct, width=10)` — bar width and the `▰▱` characters
- The labels `5ч` / `нед` / `$лим` and the `ctx` / `out` prefixes live in `main()`

---

## По-русски

Статусная строка для Claude Code: модель, использование контекстного окна, стоимость
сессии и **лимиты подписки** — 5-часовое и недельное окна с процентом и временем до
сброса. Один файл, только стандартная библиотека Python.

Установка — скопировать `statusline.py` в `~/.claude/` и добавить блок `statusLine`
в `~/.claude/settings.json` (см. раздел Install выше).

Лимиты появляются после первого ответа модели в сессии. Для API-аккаунтов вместо них
показывается лимит трат. Цвета: синий → бирюзовый → оранжевый (70%) → красный (90%),
подобраны так, чтобы читаться на светлой теме и различаться при дальтонизме.

## License

MIT
