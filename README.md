# 大肥鱼桌宠 🐋

English | [中文](README.md) → [README.en.md](README.en.md)

## ⬇️ 下载即用（Windows）

[![最新版本](https://img.shields.io/github/v/release/RYANFFY/dafeiyu-pet?label=%E6%9C%80%E6%96%B0%E7%89%88%E6%9C%AC)](https://github.com/RYANFFY/dafeiyu-pet/releases/latest)
[![下载量](https://img.shields.io/github/downloads/RYANFFY/dafeiyu-pet/total?label=%E4%B8%8B%E8%BD%BD%E9%87%8F)](https://github.com/RYANFFY/dafeiyu-pet/releases)

### 👉 [**点这里下载最新版 exe**](https://github.com/RYANFFY/dafeiyu-pet/releases/latest/download/dafeiyu-pet.exe)

约 60MB 单文件，**双击就能用，不需要安装 Python**。（这个链接永远指向最新版，可以直接收藏）

- 首次运行 Windows 可能提示"未知发布者"（exe 没做代码签名）→ 点「更多信息」→「仍要运行」即可
- 想看历史版本 / 更新说明：[Releases 页面](https://github.com/RYANFFY/dafeiyu-pet/releases) ｜ [CHANGELOG](CHANGELOG.md)
- 打包版的设置写在 `%APPDATA%\大肥鱼桌宠\`（不会往桌面丢文件）
- 用完想卸载：删掉 exe + 上面那个配置目录就行

DeepSeek V4 Pro 二创形象「鲸鱼娘·大肥鱼」的透明桌面宠物。

基于三视图素材（正面 / 侧面 / 背面），用 Python + PySide6 实现，无边框透明置顶窗口。

## 功能

- **三视图行走**：左右走用侧面（自动镜像）、向上走用背面、向下走用正面

- **三种模式**：自由散步 / 跟随鼠标 / 原地待着（右键菜单切换）

- **层级可选**：置顶 / 置底（沉到所有窗口下面，但仍在壁纸和 Wallpaper Engine 这类桌面软件之上）/ 普通层

- **透明度可调**：菜单里一条滑块，从 100% 到 20%（太透就看不见了，所以留了下限）

- **单实例**：已经开着一只时，再点快捷方式或再跑一次源码都不会冒出第二只（会把它叫出来）

- **进程联动**：打开 Steam / WeGame / 浏览器 / 播放器这些应用时，它会冒泡吐槽两句。
  菜单「进程联动 → 扫描电脑应用并添加…」会打开一个**带图标的可视列表**（像「设置 → 应用」）：
  每个应用都显示自己的图标、顶部可搜索；`●内置默认` 的应用已经自带台词（**不能重复添加**，
  但可以点「修改默认台词」改写，改完整组替换、可一键「恢复内置台词」），
  `✓已添加` 是你自己加的应用，可以修改或删除

- **互动**：
  - 左键按住：拖拽（会侧身朝向拖动方向，松手会说话）
  - 单击：蹦跳 + 回嘴（互动台词）+ 顺手刷新余额
  - 右键：完整菜单（模式 / 大小 / 形象 / 天气 / 余额 / 音效 / 显示隐藏 / 鼠标穿透 / 置顶 / 开机自启 / 退出；托盘右键是同款菜单，穿透后可从托盘解除）

- **台词系统**：日常随机台词 + 互动回嘴 + 思维链心声（灰色斜体括号气泡，小概率冒出），全部取材自社区 DS 梗

- **细节**：呼吸 / 摇摆 / 蹦跳动画、转向交叉淡化、加减速惯性、散步自动休息、说话冷却；移动时整个窗口（含上方气泡区）都留在屏幕内

- 托盘图标、窗口置顶、鼠标穿透、开机自启、配置记忆（config.json）；穿透 / 置顶状态重启后自动恢复

  ##### 天气（联网）

  - 右键菜单「天气 → 查看天气」→ 调用 `wttr.in` 播报「汕头今天 26°，天气晴」
  - 「天气 → 设置默认城市（手动输入）」：直接填城市名（中文英文都行）写进 `config.json` 当默认城市，不联网
  - 「天气 → 添加城市（联网搜索）」：输入城市名后先查 open-meteo 地理编码给候选列表；中文地名搜不到时用 wttr.in 验证能不能查到，选中的城市写进 `config.json`
  - 「天气 → 自动定位城市」：按 IP 联网定位（挂梯子会定位到节点所在地，菜单里也标了），英文城市名会自动换成中文（Singapore → 新加坡）
  - **播报全中文**：天气描述优先按 wttr.in 的天气代码（WWO code）查中文对照表，取不到再按英文关键词翻译（Patchy rain nearby → 小雨），实在认不出显示「未知天气」，不会把英文原样吐出来
  - 天气请求走后台线程，不会卡住桌宠

  > 设置类改动（城市 / 大小 / 形象 / 音效 / 音量等）会自动写回 `config.json`，不用等退出程序。

  ##### 余额挂件（新增）

  让桌宠顺便当「余额挂件」，功能对齐 [MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget)（MIT）。

  - **余额泡泡**：鱼头顶三行「DeepSeek 余额 / ¥金额 / 今日已用」，启动后自动冒一次
  - **数字滚动**：余额变化时金额从旧值缓出滚到新值
  - **自动刷新**：每 60 秒拉一次；余额有变化自动冒泡；菜单「余额 → 查看余额」可手动刷新
  - **今日已用**：小鲸鱼记账（余额差值本地记账，免平台令牌），跨天自动归零归档，账本 `usage.json`
  - **峰谷时段**：余额泡泡第四行显示「现在 高峰时段 / 空闲时段」，高峰橙红、空闲绿色，一眼看出现在贵不贵；
    菜单「余额 → 显示峰谷时段」可关，「峰谷文案」可切三档（默认 / 梁文峰谷 / !?强强?!）；跨进新时段会主动冒泡提醒
    - 规则：工作日 9:00–12:00 与 14:00–18:00 为高峰，其余（午休、晚上、周末全天）为空闲；周末全天谷价自 2026-08-23 起生效
    - 和「每轮 Codex 对话消耗」用的是同一套峰谷定价表
  - **拖拽吸附**：松手后按屏幕四分之一区域吸附左 / 右 / 上 / 下（角落可组合）
  - **左吸附翻面**：吸附到左边缘时整体水平翻转，右边缘翻回来
  - **按压 Q 弹**：按住时横向撑开、纵向压扁，底部坐标不变（不跑位）
  - **每轮 Codex 对话消耗**：读 Codex 会话日志（`~/.codex-deepseek/sessions/*.jsonl`）里的真实 token 用量，一轮结束后按峰谷定价换算并冒泡（菜单可关）
  - **余额常显**：菜单勾上后余额泡泡常驻；普通台词临时覆盖，说完自动回到余额
  - **按键音效**：**一次点击响一声完整音效**（不再检测松手）——把原来的「按压 + 松手」两段 wav 首尾拼成一条
    （`click-duck.wav` 345ms / `click-fx1.wav` 211ms），所以点一下就听得到完整一段二连音；
    快速连点就按点击间隔自然响；带音量滑块，可在菜单里关掉
  - **音效走常开音频流**：用 `QAudioSink` 常开输出、自己混音（没人点时输出静音），所以设备一直是醒的，
    不会出现「刚点下去开头那一下被吞（ya1 听不见）」。多条点击可以重叠（连点不互相打断）；
    音量是按样本缩放实现的。取不到音频设备时自动退回 `QSoundEffect`（3 个实例轮转 + 静音预热 + 未就绪补播）
    或系统 `winsound`，菜单里还有「试听音效」
- **形象切换**：菜单「形象」里在大肥鱼（三视图行走）和小鲸鱼挂件（挂件那张 cut-out）之间随时换

- **自定义形象**：菜单「形象」里两套外观都能换成你自己的图片 —— 挂件是单张图；三视图外观可以分别指定正面 / 侧面 / 背面三个视图各自的图片，随时一键恢复默认

- **多余额来源**：除了 DeepSeek，还能添加别的 API Key（DeepSeek / OpenRouter 能查到余额；像 OpenAI / ChatGPT 这种官方没开放余额接口的，会直接告诉你"该服务不提供余额接口"，而不是报错）

- **每轮消耗统计**：读会话日志里的真实 token 用量，按峰谷定价换算后冒泡。**Agent 名称和日志目录都能自己设**
  （菜单「余额 → 每轮消耗统计 → 设置 Agent 名称 / 设置会话日志目录…」），不用 Codex 的人也能用；
  日志解析兼容 Codex、Claude Code 等不同的 usage 结构

- **菜单分区**：吸附（拖拽吸附四边 / 左吸附翻面）、文案（峰谷显示与三档文案）都拆成了独立菜单，不再塞在「余额」下面
  - **气泡样式统一**：随机台词气泡和余额气泡共用同一套圆角、留白、尾巴参数

  另外：右键菜单和对话框自身带置顶标志，**打开期间桌宠会站住不动**、也不再参与置顶竞争，
  菜单还会每 400ms 把自己抬到最前 —— 所以不会再出现"设置面板被大肥鱼压住一角"。

  余额用的 Key：优先 `config.json` 里的 `ds_api_key`（右键菜单「余额 → 设置 Key」），没填则读系统环境变量 `DEEPSEEK_API_KEY`。
  峰谷定价表在 `桌宠.py` 顶部 `BASE_PRICE` / `PRO_PRICE`，DeepSeek 调价时改这里。
  音效与挂件形象素材来自上面那个 MIT 项目，放在 `assets/`（mp3 为原始文件，wav 供播放）。

## 运行

需要 **Python 3.11+**

```bash
pip install -r requirements.txt
# 或
pip install PySide6
```

然后双击 `启动桌宠.bat`，或：

```bash
python 桌宠.py
```

## 打包成独立 exe（可分享给朋友）

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name 大肥鱼桌宠 --add-data "sprites;sprites" --add-data "assets;assets" --icon icon.ico 桌宠.py
```

产物在 `dist/大肥鱼桌宠.exe`，对方双击即用，无需安装 Python。
（杀毒软件可能对 PyInstaller 产物误报，加信任即可。）

小提示：如果你自己打包后启动报 `DLL load failed while importing QtCore`，是因为
PyInstaller 把本机其它运行时里的 ICU（`icuuc.dll` / `icudt*.dll`）也打进了包，和 Qt 期望的
系统 ICU 版本冲突；`桌宠.spec` 里已经加了过滤，直接用它打包就不会踩这个坑。

## 改完代码怎么发版（维护者）

1. 双击仓库同级的「发布到GitHub.bat」（或手动提交）：
   ```bash
   git add -A && git commit -m "说明这次改了什么" && git push origin main
   ```
   网络不好时加参数：`git -c http.sslBackend=openssl -c protocol.version=0 push origin main`
2. 要发新版本（带 exe 下载）时重新打包并建 Release：
   ```bash
   pyinstaller --noconfirm --clean 桌宠.spec
   gh release create v1.0.1 "dist/大肥鱼桌宠.exe" --title "大肥鱼桌宠 v1.0.1" --notes "这次改了什么"
   ```

## 更换形象

把新的三视图（白底）放到程序目录：

1. 正面.png / 侧面.png / 背面.png（原图）
2. 运行 `python preprocess.py` —— 白底抠图 + 统一高度
3. 运行 `python preprocess2.py` —— 边缘去污 + 预乘 alpha 缩放出各尺寸精灵

## 文件说明

| 文件 | 说明 |
|------|------|
| 桌宠.py | 主程序（全部逻辑） |
| preprocess.py | 白底三视图抠图脚本 |
| preprocess2.py | 精灵边缘去污 + 多尺寸生成脚本 |
| sprites/ | 精灵图（正面/侧面/背面 各尺寸 + 图标） |
| assets/ | 音效（wav 播放 / mp3 原始）与小鲸鱼挂件形象 |
| 启动桌宠.bat | 启动脚本（自动选择 venv 或系统 Python） |
| requirements.txt | 依赖 |
| 桌宠.spec | PyInstaller 打包配置（含新依赖收集） |

## 贡献与致谢

- **AI 对话 / 天气查询 / 系统监控 / PyInstaller 打包配置**：由 [Cpanoe](https://github.com/Cpanoe) 通过 [PR#3](https://github.com/1190fasheqi/dafeiyu-pet/pull/3) 贡献（DeepSeek API 聊天、wttr.in 天气、CPU/内存/GPU 监控、桌宠.spec）。
- 合并时维护方修复：
  - 线程安全：DeepSeek 回复由后台线程直接调用 Qt 界面改为经队列转发主线程（`_say_queue`）
  - 配置保护：`config.json` 保持不入仓库（本地配置含 API Key，防止泄露）
- **本机精简改造**：按需求只保留「移动 + 天气 + 外观」，删掉 AI 对话 / 喂食 / 系统状态监控；
  再从 [MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget)（MIT）并入余额挂件那套能力
  （余额泡泡、今日已用记账、数字滚动、四边吸附、左吸附翻面、按压 Q 弹、按键音效、形象切换、每轮 Codex 消耗统计）。
- 桌面宠物朝向修复由 [B-A-A-GE](https://github.com/B-A-A-GE) 通过 [PR#1](https://github.com/1190fasheqi/dafeiyu-pet/pull/1) 提交（未合并，当前为维护方修复版）。

## 台词梗来源

台词均取自 DeepSeek / 鲸鱼娘 / 大肥鱼社区梗（D指导去吃饭、吃白饭、梁文锋会议三连、"才不是大肥鱼"、思维链心声等），感谢社区整活。

## 协议

MIT
