# AGENTS.md · 大肥鱼桌宠

这份文件是**跨对话**的项目约定。本仓库是 Codex 桌面应用的本地项目根目录，
新开对话默认从这里起步，所以需要长期保留的规则都写在这里，
不要依赖某个超长对话的历史。

## 这是什么

Windows 桌面宠物（Python + PySide6）。大肥鱼 / 小鲸鱼形象常驻桌面，
显示 DeepSeek 余额、天气、当前播放的歌曲与歌词，带右键菜单、音效、开机自启、
可换形象，可打包成 exe 与中文安装包发布。

## 常用命令

```bash
# 运行（开发）
.venv\Scripts\pythonw.exe 桌宠.py      # 或直接双击 启动桌宠.bat

# 依赖（需要 Python 3.11+）
pip install -r requirements.txt

# 打包独立 exe —— 用 spec，不要手写参数（spec 里做了 ICU 过滤）
pyinstaller --noconfirm --clean 桌宠.spec

# 打包中文安装包（Inno Setup 6）
"F:\Codex\tools\innosetup\ISCC.exe" "/DMyAppVersion=1.0.x" installer.iss
```

产物在 `dist/`，不提交。发版流程见 `README.md` 的「改完代码怎么发版」：
版本号按现有最高版本 +1，保持连续、不跳号；内容没变不重发。

## 关键文件

| 文件 | 作用 |
| --- | --- |
| `桌宠.py` | 主程序，单文件，体量很大（27 万字符级别），改前先定位到具体类/方法 |
| `config.json` | 运行时配置，**已被 .gitignore 忽略**，不要提交、不要当源码改 |
| `sprites/` `assets/` | 形象贴图与音效素材 |
| `桌宠.spec` `installer.iss` | PyInstaller / Inno Setup 打包脚本 |
| `CHANGELOG.md` | 每个版本改了什么 + 怎么验证的（含实测命令与截图路径） |
| `TODO.md` | 待办，以及「已经试过、没能解决的方案」 |
| `README.md` | 面向用户与维护者的说明 |

## 这个项目的习惯（请沿用）

- 交流、注释、提交信息都用中文。commit 风格：`feat: …` / `fix: …` / `perf: …` + 中文说明。
- 每次改动同步更新 `CHANGELOG.md`（写清改了什么、怎么验证）和 `TODO.md`。
- **验证方式要落到实测**：离屏脚本用 `F:\Codex\work\test_*.py`，真机探测用 `probe_*.py`，
  截图存 `shot_*.png` —— 这些放 `F:\Codex\work`，不要塞进仓库。
- 改动右键菜单（尤其新增二级菜单）后，必须用真鼠标点一遍子菜单。
- `dist/` `build/` `.venv/` `__pycache__/` 以及运行时文件（`config.json`、`usage.json`、
  `lyrics_cache.json`、`menu-debug.log`）都不提交。
- 用户的反馈常带截图和具体时间点，照原话记进 TODO / CHANGELOG，别改写成自己的说法。

## 已知的坑（别重复踩）

- **二/三级子菜单**：Qt 弹出菜单拿不到鼠标捕获，悬停兜底、事件转发、延时关闭、
  原生消息层拦截、改成浮窗/对话框等方案都试过且无效。v1.0.10 起改为
  自己实现菜单窗口 + 自己持有捕获。细节在 `TODO.md` 末尾。
- **打包报 `DLL load failed while importing QtCore`**：PyInstaller 把本机其它运行时的
  ICU 打进了包。用 `桌宠.spec`（已加过滤）而不是手写命令行。
- **歌词**：网易云不报时间轴时按播放器时间对齐；切歌前不猜进度、失败不清空缓存。
- `make_zip.py` 里的 `BASE` / `OUT` 还是旧机器路径（`D:\图图\大肥鱼\…`），
  在当前位置要用得先改这两个常量。

## 对话与分支

- 一个任务开一个新对话，做完归档；用项目而不是用超长对话来保存上下文。
- 不要靠「分支」把整段历史带进新对话 —— 分支会继承父对话的全部历史，
  历史越大越容易撞上接口的请求体上限（413）。
