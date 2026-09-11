# 更新日志

## v1.0.2

- **层级可选**：置顶 / 置底（在所有窗口下面，但仍在壁纸和 Wallpaper Engine 这类桌面软件之上）/ 普通层
- **透明度可调**：菜单里一条滑块，100% → 20%
- **自由散步更灵**：只要横向有位移就走侧面，不再"背过身去不转回来"；原地待着时会转头看鼠标
- **进程联动**：检测到 Steam / WeGame / 浏览器 / 播放器 / 编辑器等被打开时，冒泡吐槽一句
  （台词表在 `桌宠.py` 顶部 `PROCESS_LINES`，可以自己加；菜单里可整体关掉）
- **单实例**：已开着一只时再点快捷方式或再跑源码都不会冒出第二只，会把它叫出来
- **自定义形象**：菜单「形象」里两套外观都能换成自己的图片 —— 挂件是单张图，
  大肥鱼三视图可以分别指定正面 / 侧面 / 背面，随时一键恢复默认
- **多余额来源**：可添加别的 API Key。DeepSeek 与 OpenRouter 能查到余额（OpenRouter 按 credits − usage 算）；
  OpenAI / ChatGPT 这类官方没有余额接口的，会直接显示"该服务不提供余额接口"，而不是报错
- 仓库首页加了醒目的下载入口；Release 附件名固定为 `dafeiyu-pet.exe`，
  所以 `releases/latest/download/dafeiyu-pet.exe` 永远指向最新版

## v1.0.1

- 打包修复：PyInstaller 会把本机其它运行时的 ICU（`icuuc.dll` / `icudt78.dll`）打进包，
  与 Qt 期望的系统 ICU 版本冲突，启动即报 `DLL load failed while importing QtCore`；
  `桌宠.spec` 现在会过滤这些 DLL，并补齐 PySide6 自带但会被漏收的 MSVC 运行库
- 新增英文说明 `README.en.md`
- 文档补充：打包踩坑说明、维护者发版流程
- 打包版 exe 体积约 60MB，配置写在 `%APPDATA%\大肥鱼桌宠\`

## v1.0.0

首个发布版本：

- 桌宠本体：三视图行走（左右镜像 / 向上背面 / 向下正面）、自由散步 / 跟随鼠标 / 原地待着
- 余额挂件：余额泡泡（余额 / 今日已用 / 当前峰谷时段）、数字滚动、每 60 秒自动刷新、点击手动刷新
- 拖拽四边吸附 + 左吸附整体翻转 + 按压 Q 弹 + 按键音效（按压+松手合并成一条完整音频，常开音频流播放）
- 每轮 Codex 对话消耗统计（读会话日志，按峰谷定价换算）
- 天气：手动设默认城市 / 联网搜索 / 按 IP 定位，播报全中文，wttr.in + open-meteo 双源
- 形象切换：大肥鱼（三视图）/ 小鲸鱼挂件（cut-out）
- 按需求精简：移除 AI 对话、喂食、系统状态监控

基于 [1190fasheqi/dafeiyu-pet](https://github.com/1190fasheqi/dafeiyu-pet)（MIT）改造，
余额挂件能力与素材并入自 [MeteorNOX/DeepSeek-Balance-Whale-Widget](https://github.com/MeteorNOX/DeepSeek-Balance-Whale-Widget)（MIT）。
