# Da Fei Yu Desktop Pet 🐋

中文版说明见 [README.md](README.md)。

## ⬇️ Download (Windows)

[![latest release](https://img.shields.io/github/v/release/RYANFFY/dafeiyu-pet?label=latest)](https://github.com/RYANFFY/dafeiyu-pet/releases/latest)

### 👉 [**Download the latest exe**](https://github.com/RYANFFY/dafeiyu-pet/releases/latest/download/dafeiyu-pet.exe)

Single file, ~60MB, just double-click — no Python required.

- Windows may warn about an unknown publisher (the exe is not code-signed): click "More info" → "Run anyway"
- Packaged build keeps its settings in `%APPDATA%\大肥鱼桌宠\`
- All versions and release notes: [Releases](https://github.com/RYANFFY/dafeiyu-pet/releases)

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
- **Menus**: snapping and the peak wording switcher live in their own top-level menus (吸附 / 文案), no longer buried under 余额

**Weather**

- Manual default city, online city search, or IP-based auto locate; all announcements are in Chinese
- Weather text is mapped from WWO/WMO weather codes with an English-keyword fallback, `wttr.in` plus `open-meteo` as a backup source

**Appearance**

- Switch anytime between 大肥鱼 (three-view sprite) and 小鲸鱼挂件 (the widget's cut-out art)
- Bring your own art: pick a picture for the widget skin, or set each of the three views (front / side / back) separately

**Window**

- Layer: always-on-top / bottom-most (still above the wallpaper) / normal
- Opacity slider (100% → 20%)
- Single instance: launching the shortcut again won't spawn a second pet

**Other**

- Process reactions: it comments when you switch to Steam, your browser, a player, etc.
  Menu "进程联动 → 扫描电脑应用并添加…" opens a **visual list with real app icons** (searchable, like Windows Settings → Apps):
  built-in apps are marked `● built-in (can't be added twice)` but you can **edit their lines** (`修改默认台词`, replacing the
  built-in text, with one-click `恢复内置台词`), and any other app can get your own trigger text
- Multiple balance sources: add another API key (DeepSeek and OpenRouter can be queried; services like OpenAI have no balance API and it will tell you so)
- **Per-turn cost is agent-agnostic**: set the **agent name** (shows as "last turn Claude cost ¥…") and the **session log
  directory** from the menu; the log parser understands Codex (`payload.usage`), Claude Code (`message.usage`) and
  OpenAI-style (`prompt_tokens`/`completion_tokens`) records

**Right-click menu** (top level): 模式 / 大小 / 形象 / 吸附 / 文案 / 天气 / 余额 / 音效 / 层级 / 透明度 / 进程联动 /
显示隐藏 / 回到屏幕内 / 鼠标穿透 / 开机自启 / 退出

- 吸附: snap to edges / flip when snapped left　文案: peak-off-peak display and its three wording styles
- 层级: always-on-top / bottom-most / normal　透明度: 100% → 20%
- 形象: switch skins, and replace any of the three views or the cut-out with your own picture

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
