# Da Fei Yu Desktop Pet 🐋

中文版说明见 [README.md](README.md)。

A transparent always-on-top desktop pet based on the DeepSeek fan-art character
「鲸鱼娘 · 大肥鱼」, built with Python + PySide6. It walks around your desktop,
tells you the weather, and doubles as a **DeepSeek balance widget**
(balance, today's spend, peak/off-peak hours, per-turn cost).

This repository is a slimmed-down fork of
[1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet) (MIT),
with the balance-widget features ported from
[MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget) (MIT).

## Features

**Pet**

- Three-view walking: side view for left/right (auto mirrored), back view when walking up, front view when walking down
- Three modes: free roam / follow the mouse / stay in place
- Drag it around (it leans toward the drag direction and says something when you let go)
- Single click: hop + talk back + refresh the balance
- Tray icon, always-on-top, click-through mode, start with Windows, settings persisted in `config.json`

**Balance widget**

- Balance bubble above its head: `DeepSeek balance / ¥amount / today's spend / current peak or off-peak`
- Rolling number animation when the balance changes, auto refresh every 60s (click the pet to refresh now)
- Today's spend is tracked locally from balance drops (no platform token needed), resets daily, ledger in `usage.json`
- Drag to snap to screen edges (four quarters, corners allowed), flips horizontally when snapped left
- Squash-and-stretch when pressed; keeps its feet on the ground
- Click sounds: press + release clips merged into one complete sound, played through an always-open audio stream (no clipped first note, rapid clicks overlap)
- **Peak / off-peak indicator**: weekday 09:00–12:00 and 14:00–18:00 are peak, everything else (lunch break, evenings, weekends all day) is off-peak; three wording styles, and it tells you when the period switches
- **Per-turn cost**: reads the token usage from Codex session logs (`~/.codex-deepseek/sessions/*.jsonl`), converts it with the same peak/off-peak pricing table and reports it after each turn

**Weather**

- Manual default city, online city search, or IP-based auto locate; all announcements are in Chinese
- Weather text is mapped from WWO/WMO weather codes with an English-keyword fallback, `wttr.in` plus `open-meteo` as a backup source

**Appearance**

- Switch anytime between 大肥鱼 (three-view sprite) and 小鲸鱼挂件 (the widget's cut-out art)

## Requirements

- Windows, Python 3.11+
- `pip install -r requirements.txt` (PySide6 + requests)

## Run

```bash
python 桌宠.py
```

or double-click `启动桌宠.bat`.

The DeepSeek API key is read from `config.json` (`ds_api_key`, set it via the
right-click menu → 余额 → 设置 Key) or from the `DEEPSEEK_API_KEY` environment variable.

## Build a standalone exe

```bash
pip install pyinstaller
pyinstaller --noconfirm 桌宠.spec
```

The result is `dist/大肥鱼桌宠.exe` — a single portable executable that needs no
Python install. Settings of the packaged build live in
`%APPDATA%\大肥鱼桌宠\` instead of next to the exe.

## Credits

- Original pet, sprites and lines: [1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet) (MIT)
- Balance widget design, sounds and the cut-out art: [MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget) (MIT)
- AI chat / weather / system monitor / PyInstaller config in the original project: [Cpanoe](https://github.com/Cpanoe) (PR#3)
- Facing fix: [B-A-A-GE](https://github.com/B-A-A-GE) (PR#1)

## License

MIT — see [LICENSE](LICENSE).
