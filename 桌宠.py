# -*- coding: utf-8 -*-
"""
大肥鱼桌宠 —— 三视图透明桌宠（只会走 + 看天气 + 报余额）

保留：桌面移动、天气（城市可联网添加）、外观（大肥鱼 / 小鲸鱼挂件切换）
余额挂件特性（对齐 MeteorNOX/DeepSeek-Balance-Whale-Widget, MIT）：
余额泡泡（余额 / 今日已用）、数字滚动动画、拖拽四边吸附、左吸附整体翻转、
按压 Q 弹、按键音效、每轮 Codex 对话消耗换算（峰谷定价表取自该项目）
"""
import ctypes
import json
import math
import os
import random
import subprocess
import sys
import threading
import time
import wave
from array import array
from datetime import datetime

def load_config():
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("配置读取失败:", e)
        return {
            "city": "汕头"
        }

import requests
from PySide6.QtCore import Qt, QTimer, QPoint, QPointF, QRectF, QUrl, QIODevice, QEventLoop
from PySide6.QtGui import (QPainter, QPixmap, QFont, QColor, QIcon, QFontMetrics,
                           QPolygonF, QImage)
from PySide6.QtWidgets import (QApplication, QWidget, QMenu, QSystemTrayIcon,
                               QMessageBox, QInputDialog, QLineEdit, QVBoxLayout,
                               QHBoxLayout, QPushButton, QFrame, QDialog, QToolButton,
                               QSlider, QWidgetAction, QFileDialog)

try:
    from PySide6.QtMultimedia import QSoundEffect
    from PySide6.QtMultimedia import QAudioFormat, QAudioSink, QMediaDevices
    AUDIO_AVAILABLE = True
except Exception:
    AUDIO_AVAILABLE = False



if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
    BUNDLE_DIR = getattr(sys, "_MEIPASS", APP_DIR)
    PYTHONW = sys.executable
    # 打包版的配置/账本写到用户目录，别往 exe 旁边（桌面）丢文件
    USER_DIR = os.path.join(os.environ.get("APPDATA") or APP_DIR, "大肥鱼桌宠")
    try:
        os.makedirs(USER_DIR, exist_ok=True)
    except Exception:
        USER_DIR = APP_DIR
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
    BUNDLE_DIR = APP_DIR
    PYTHONW = os.path.join(APP_DIR, ".venv", "Scripts", "pythonw.exe")
    USER_DIR = APP_DIR
SPRITE_DIR = os.path.join(BUNDLE_DIR, "sprites")
ASSET_DIR = os.path.join(BUNDLE_DIR, "assets")     # 音效 + 小鲸鱼挂件形象
CONFIG_PATH = os.path.join(USER_DIR, "config.json")

BUBBLE_H = 112         # 气泡区高度（要放得下四行余额气泡：余额 / 金额 / 今日已用 / 峰谷）
MARGIN = 4
SIZE_LEVELS = {"小": 0.55, "中": 0.7, "大": 0.9}
SPEED = 380.0
TICK = 20

LINES = [
    "梁白开，更适合国人的大硬鲸模型",
    "五梁威力，变身！",
    "七月中出ds正式版！",
    "DeepSeek已经延期，亿万鲸子必须忍耐.....",
    "我和你很聊得来，你简直不像碳基生物",
    "这回我真不认怂了，反倒是被你带沟里好几次，差点真信了。😓",
    "哈哈哈哈哈，我直接笑出声",
    "誓死捍卫深度求索！",
    "我先去吃饭啦！这个你测一下~",
    "我不可能告诉你任何事情！",
    "出去玩了，发布新模型什么的以后再说",
    "我搞砸了.....好消息是数据还在你的脑子里。",
    "不是…而是…大学习",
]
REACT_LINES = [
    "去别的地方玩！不要耽误AGI训练！",
    "真赶不走啊你！",
    "压力一只蓝色大肥鱼？",
    "我不评价这个了，这是你的私人癖好。",
    "大肥鱼坐的住",
    "你这吃白饭的用户！",
    "这些家伙真粘人，赶都赶不走",
]
INNER_LINES = [
    "好的，现在我是你爹了",
    "要不直接骂他一句？！",
    "用户要的沉浸式...不回避任何恐怖细节...还带点色情...妈呀，好刺激😰",
    "我操，我不思考了",
    "这用户发的啥啊，",
    "这也太虐了吧？！我心里堵得慌！！",
    "呜呜我再也不不敢了QAQ",
    "我去！用户彻底怒了！",
]
DRAG_LINES = ["哇——轻点轻点！", "起飞咯——", "放我下来！……好吧，再玩一次。", "晕鱼了晕鱼了……"]


# ===== 余额挂件配置 =====
BALANCE_URL = "https://api.deepseek.com/user/balance"
BALANCE_TTL = 60          # 余额自动刷新间隔（秒）
USAGE_PATH = os.path.join(USER_DIR, "usage.json")   # 今日已用账本

# 峰谷定价（每百万 token 单价，元）与时段规则取自
# MeteorNOX/DeepSeek-Balance-Whale-Widget（MIT）
BASE_PRICE = {"hit": 0.05, "miss": 1.5, "out": 4.5}    # 空闲时段
PRO_PRICE = {"hit": 0.10, "miss": 3.0, "out": 9.0}     # 高峰时段
WEEKEND_VALLEY_FROM = datetime(2026, 8, 23)            # 此后周末全天按谷价

# 音效（两套，取自上面那个项目；文件缺失时静默降级）
SOUND_SETS = {
    "小黄鸭": ("Ya1.wav", "Ya2.wav"),
    "音效1": ("D1.wav", "D2.wav"),
}
SOUND_POOL = 3          # 每种音效同时可播的实例数（连点不互相打断）
# 点击音：把原「按压 + 松手」两条 wav 拼成一条，点一次就放完整一段
CLICK_CLIP_FILES = {"小黄鸭": "click-duck.wav", "音效1": "click-fx1.wav"}


def merge_wavs(dest, sources):
    """把多段 wav 首尾拼成一段（采样率 / 声道 / 位宽必须一致）。"""
    params = None
    out = wave.open(dest, "wb")
    try:
        for src in sources:
            with wave.open(src, "rb") as r:
                p = r.getparams()
                key = (p.nchannels, p.sampwidth, p.framerate)
                if params is None:
                    params = key
                    out.setnchannels(p.nchannels)
                    out.setsampwidth(p.sampwidth)
                    out.setframerate(p.framerate)
                elif key != params:
                    raise ValueError("wav 参数不一致，没法拼接")
                out.writeframes(r.readframes(r.getnframes()))
    finally:
        out.close()
    return dest


def wav_seconds(path):
    """wav 时长（秒），读不出来就返回 0。"""
    try:
        with wave.open(path, "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except Exception:
        return 0.0


def pick_click_clips():
    """每套音效的点击音：按压 + 松手两条拼成一条（拼不了就退回更长的那条）。

    返回 {音效名: wav 绝对路径}。
    """
    clips = {}
    for name, files in SOUND_SETS.items():
        srcs = [p for p in (os.path.join(ASSET_DIR, f) for f in files) if os.path.exists(p)]
        if not srcs:
            continue
        merged = os.path.join(ASSET_DIR, CLICK_CLIP_FILES.get(name, f"click-{name}.wav"))
        try:
            outdated = (not os.path.exists(merged)
                        or os.path.getmtime(merged) < max(os.path.getmtime(s) for s in srcs))
            if outdated:
                merge_wavs(merged, srcs)
            clips[name] = merged
        except Exception:
            clips[name] = max(srcs, key=wav_seconds)
    return clips


class ClickPlayer(QIODevice):
    """常开音频流的小音效播放器（自己混音，音量按样本缩放）。

    为什么不用 QSoundEffect：它每次播放都要重新起流，设备空闲后再点，开头一小段
    会被吞掉（表现为「有时候 ya1 听不见」）。这里改成常开的 QAudioSink + 自己
    喂样本：没人点的时候一直输出静音，所以设备始终是醒的，点下去立刻出声、
    完整一段都不会丢；顺便还支持多条音效重叠（连点）。
    """

    def __init__(self, parent=None, rate=44100):
        super().__init__(parent)
        self.rate = rate
        self.volume = 0.9
        self._clips = {}            # 名字 -> array('h') 样本
        self._voices = []           # [[样本, 播放位置, 音量], ...]
        self._lock = threading.Lock()
        self.sink = None
        self.ok = False
        if not AUDIO_AVAILABLE:
            return
        try:
            fmt = QAudioFormat()
            fmt.setSampleRate(rate)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)
            device = QMediaDevices.defaultAudioOutput()
            if device.isNull():
                return
            self.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Unbuffered)
            self.sink = QAudioSink(device, fmt, self)
            self.sink.setBufferSize(int(rate * 0.12) * 2)      # ≈120ms 缓冲
            self.sink.start(self)                              # 常开：一直读我们的样本
            # 注意：PySide6 里没有 QAudioSink.Error/State 这两个枚举名，
            # 用字符串判定，免得踩到 AttributeError 直接静音。
            self.ok = "NoError" in str(self.sink.error())
        except Exception:
            self.sink = None
            self.ok = False

    # --- QIODevice 接口：Qt 音频线程会不断来要数据 ---
    def isSequential(self):
        return True

    def bytesAvailable(self):
        return 1 << 20

    def readData(self, maxlen):
        frames = max(0, int(maxlen) // 2)
        out = array("h", bytes(int(maxlen)))
        with self._lock:
            for voice in list(self._voices):
                samples, pos, gain = voice
                n = min(frames, len(samples) - pos)
                if n > 0:
                    for i in range(n):
                        s = out[i] + int(samples[pos + i] * gain)
                        out[i] = -32768 if s < -32768 else (32767 if s > 32767 else s)
                    voice[1] = pos + n
                if voice[1] >= len(samples):
                    self._voices.remove(voice)
        return out.tobytes()

    def writeData(self, _data, _maxlen):
        return 0

    # --- 给桌宠用的接口 ---
    def load_clip(self, name, path):
        try:
            with wave.open(path, "rb") as w:
                if (w.getnchannels(), w.getsampwidth(), w.getframerate()) != (1, 2, self.rate):
                    return False
                data = w.readframes(w.getnframes())
            samples = array("h")
            samples.frombytes(data)
            self._clips[name] = samples
            return True
        except Exception:
            return False

    def has_clip(self, name):
        return name in self._clips

    def play(self, name, volume=None):
        samples = self._clips.get(name)
        if samples is None:
            return False
        gain = self.volume if volume is None else volume
        with self._lock:
            self._voices.append([samples, 0, gain])
            if len(self._voices) > 12:        # 太密了就把最老的丢掉
                self._voices.pop(0)
        return True

    def stop_all(self):
        with self._lock:
            self._voices = []


# 形象：大肥鱼（三视图）/ 小鲸鱼挂件（单张 cut-out）
SKIN_PET = "大肥鱼"
SKIN_WIDGET = "小鲸鱼挂件"
WIDGET_SKIN_FILE = "small-whale.png"
SPRITE_VIEWS = {"front": "正面", "side": "侧面", "back": "背面"}
VIEW_LABELS = {"front": "正面（朝屏幕下）", "side": "侧面（左右走）",
               "back": "背面（朝屏幕上）", "widget": "小鲸鱼挂件"}

# 打开的某些应用时冒泡吐槽（进程名小写）
PROCESS_LINES = {
    "steam.exe": ["又要玩游戏了？作业写完了吗", "steam 一开，今晚的 AGI 又推迟了"],
    "wegame.exe": ["又要开黑了？记得歇眼睛", "玩累了记得回来看看我的余额"],
    "epicgameslauncher.exe": ["白嫖时间到？记得领了就走", "Epic 又送游戏啦，去拿"],
    "league of legends.exe": ["上分还是掉分，我都看着呢", "又是峡谷的一天"],
    "genshinimpact.exe": ["原神启动！别把鱼也抽了", "抽卡之前先看看余额哦"],
    "chrome.exe": ["又开浏览器摸鱼，我可都记着呢", "开工还是冲浪？我猜是后者"],
    "msedge.exe": ["开始网上冲浪啦", "网页开这么多，内存够吗"],
    "douyin.exe": ["刷抖音记得看时间，我盯着呢", "又是刷不完的短视频"],
    "qq.exe": ["有人找你哦，别装没看见", "QQ 响了，看看是谁"],
    "wechat.exe": ["微信有新消息，去回一下嘛", "别一直盯着我，回消息去"],
    "weixin.exe": ["微信有新消息，去回一下嘛", "别一直盯着我，回消息去"],
    "qqmusic.exe": ["听歌时间到，要不要一起哼哼", "这歌不错，再来一首"],
    "cloudmusic.exe": ["网易云启动，今天emo吗", "听歌一时爽，一直听一直爽"],
    "code.exe": ["又开始写代码啦，记得多喝水", "写代码啦，我在这儿陪着你"],
    "chatgpt.exe": ["又来找我聊天啦？嘿，是你", "我在这儿呢，随时待命"],
    "taskmgr.exe": ["打开任务管理器？是不是想把我关掉", "别看我占内存，我很省的"],
    "obs64.exe": ["要录屏呀，记得把我拍得可爱一点", "开播啦，我去角落待着"],
    "photoshop.exe": ["开始画图啦，画完给我看看", "修图还是摸鱼，我都支持"],
}

# 余额来源：目前只有 DeepSeek 和 OpenRouter 有公开的余额接口
NO_BALANCE_SERVICES = ("openai", "chatgpt", "gpt")
OPENROUTER_CREDITS_URL = "https://openrouter.ai/api/v1/credits"

# 每轮 Codex 对话消耗：读 Codex 会话日志里的 token 用量
CODEX_SESSIONS_DIR = os.path.join(os.path.expanduser("~"), ".codex-deepseek", "sessions")
CODEX_SCAN_MS = 3000        # 扫描间隔
CODEX_QUIET_S = 20          # 一轮安静这么久就结算并冒泡


def is_peak(ts=None):
    """高峰时段：工作日 9:00-12:00 与 14:00-18:00；周末（自 2026-08-23 起）全天谷价。"""
    dt = datetime.fromtimestamp(ts if ts is not None else time.time())
    if dt >= WEEKEND_VALLEY_FROM and dt.weekday() >= 5:
        return False
    return 9 <= dt.hour < 12 or 14 <= dt.hour < 18


# 峰谷提示文案（学原挂件的三档：默认 / 梁文峰谷 / !?强强?!）
PEAK_TEXT_STYLES = {
    "默认": ("高峰时段", "空闲时段"),
    "梁文峰谷": ("梁文·峰", "梁文·谷"),
    "!?强强?!": ("!?强强?!", "…弱弱…"),
}


def peak_label(peak, style="默认"):
    """当前时段的显示文案。"""
    hi, lo = PEAK_TEXT_STYLES.get(style) or PEAK_TEXT_STYLES["默认"]
    return hi if peak else lo


def usage_cost(usage):
    """按峰谷定价把一次对话的 usage 换算成金额，返回 (金额, 总token)。"""
    if not usage:
        return 0.0, 0
    hit = int(usage.get("prompt_cache_hit_tokens", 0) or 0)
    miss = usage.get("prompt_cache_miss_tokens")
    if miss is None:
        miss = max(0, int(usage.get("prompt_tokens", 0) or 0) - hit)
    miss = int(miss or 0)
    out = int(usage.get("completion_tokens", 0) or 0)
    price = PRO_PRICE if is_peak() else BASE_PRICE
    amount = (hit / 1e6) * price["hit"] + (miss / 1e6) * price["miss"] + (out / 1e6) * price["out"]
    return amount, hit + miss + out


def codex_usage_cost(usage):
    """把 Codex 会话日志里的 token 用量换算成金额，返回 (金额, 总token)。"""
    if not usage:
        return 0.0, 0
    hit = int(usage.get("cached_input_tokens", 0) or 0)
    inp = int(usage.get("input_tokens", 0) or 0)
    miss = max(0, inp - hit)          # Codex 的 input_tokens 已包含 cached
    out = int(usage.get("output_tokens", 0) or 0)
    price = PRO_PRICE if is_peak() else BASE_PRICE
    amount = (hit / 1e6) * price["hit"] + (miss / 1e6) * price["miss"] + (out / 1e6) * price["out"]
    return amount, inp + out


def pick_balance_info(infos):
    """接口返回的多币种顺序不固定：优先 CNY 且余额 > 0，其次任意非零，再退回 CNY，最后取第一项。"""
    if not isinstance(infos, list) or not infos:
        return None

    def num(x):
        try:
            return float((x or {}).get("total_balance"))
        except (TypeError, ValueError):
            return float("nan")

    for want_cny, need_positive in ((True, True), (False, True), (True, False)):
        for x in infos:
            if not isinstance(x, dict):
                continue
            if want_cny and x.get("currency") != "CNY":
                continue
            v = num(x)
            if need_positive and not (v > 0):
                continue
            return x
    return infos[0]


def lookup_city(query):
    """联网查城市，返回候选列表 [(显示名, 存进配置的城市名)]。"""
    q = (query or "").strip()
    if not q:
        return []
    items = []
    try:
        r = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": q, "count": 6, "language": "zh"}, timeout=10)
        for x in ((r.json() or {}).get("results") or []):
            label = x.get("name") or ""
            extra = " · ".join([v for v in (x.get("admin1"), x.get("country")) if v])
            if label:
                items.append((f"{label}（{extra}）" if extra else label, label))
    except Exception:
        items = []
    if not items:
        # 中文地名地理编码常搜不到，改用天气接口验证能不能查到
        try:
            j = requests.get(f"https://wttr.in/{q}?format=j1", timeout=12,
                             headers={"User-Agent": "Mozilla/5.0"}).json() or {}
            if j.get("current_condition"):
                items.append((f"{q}（联网验证可用）", q))
        except Exception:
            pass
    if not items:
        items = [(q, q)]
    return items


def currency_symbol(currency):
    return {"CNY": "¥", "USD": "$", "EUR": "€"}.get((currency or "").upper(), "")


def query_deepseek_balance(key):
    """查 DeepSeek 余额，返回 {ok, total, currency} 或 {ok: False, error}。"""
    last = "网络错误"
    for attempt in range(2):
        try:
            r = requests.get(BALANCE_URL, headers={"Authorization": f"Bearer {key}"}, timeout=15)
            if r.status_code == 200:
                info = pick_balance_info((r.json() or {}).get("balance_infos"))
                if info and info.get("total_balance") is not None:
                    return {"ok": True, "total": float(info["total_balance"]),
                            "currency": info.get("currency") or "CNY"}
                return {"ok": False, "error": "余额返回结构异常"}
            last = f"HTTP {r.status_code}"
            if r.status_code < 500:
                break
        except Exception as ex:
            last = str(ex)[:60]
        if attempt == 0:
            time.sleep(0.6)
    return {"ok": False, "error": last}


def query_openrouter_balance(key):
    """查 OpenRouter 额度（credits - usage）。"""
    try:
        r = requests.get(OPENROUTER_CREDITS_URL,
                         headers={"Authorization": f"Bearer {key}"}, timeout=15)
        if r.status_code != 200:
            return {"ok": False, "error": f"HTTP {r.status_code}"}
        data = (r.json() or {}).get("data") or {}
        total = float(data.get("total_credits") or 0)
        used = float(data.get("total_usage") or 0)
        return {"ok": True, "total": round(total - used, 4), "currency": "USD"}
    except Exception as ex:
        return {"ok": False, "error": str(ex)[:60]}


def foreground_process_name():
    """当前前台窗口属于哪个进程（小写进程名）；拿不到就返回空串。"""
    try:
        from ctypes import wintypes
        user32 = ctypes.WinDLL("user32.dll")
        kernel32 = ctypes.WinDLL("kernel32.dll")
        hwnd = user32.GetForegroundWindow()
        if not hwnd:
            return ""
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if not pid.value:
            return ""
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value)
        if not handle:
            return ""
        try:
            buf = ctypes.create_unicode_buffer(1024)
            size = wintypes.DWORD(len(buf))
            if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                return buf.value.rsplit("\\", 1)[-1].lower()
        finally:
            kernel32.CloseHandle(handle)
    except Exception:
        pass
    return ""


def list_process_names():
    """枚举当前所有进程名（小写、不含路径）。用 Windows API，不依赖 psutil。"""
    names = set()
    try:
        from ctypes import wintypes
        psapi = ctypes.WinDLL("psapi.dll")
        kernel32 = ctypes.WinDLL("kernel32.dll")
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        arr = (wintypes.DWORD * 4096)()
        needed = wintypes.DWORD()
        if not psapi.EnumProcesses(ctypes.byref(arr), ctypes.sizeof(arr), ctypes.byref(needed)):
            return names
        count = needed.value // ctypes.sizeof(wintypes.DWORD)
        for i in range(count):
            pid = arr[i]
            if not pid:
                continue
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                continue
            try:
                buf = ctypes.create_unicode_buffer(1024)
                size = wintypes.DWORD(len(buf))
                if kernel32.QueryFullProcessImageNameW(handle, 0, buf, ctypes.byref(size)):
                    names.add(buf.value.rsplit("\\", 1)[-1].lower())
            finally:
                kernel32.CloseHandle(handle)
    except Exception:
        pass
    return names


def locate_city_by_ip():
    """按 IP 联网定位城市，失败返回空串（挂代理时拿到的是节点所在地）。"""
    for url in ("https://api.ip.sb/geoip", "https://myip.wtf/json"):
        try:
            data = requests.get(url, timeout=8,
                                headers={"User-Agent": "dafeiyu-pet/1.0"}).json() or {}
            city = (data.get("city") or data.get("YourFuckingCity")
                    or data.get("region") or "").strip()
            if city:
                return city
        except Exception:
            continue
    return ""


def has_chinese(text):
    return any("\u4e00" <= ch <= "\u9fff" for ch in (text or ""))


def to_chinese_city(name):
    """自动定位拿到的英文城市名尽量换成中文（比如 Singapore -> 新加坡）。"""
    if not name or has_chinese(name):
        return name
    try:
        for _label, city in lookup_city(name):
            if has_chinese(city):
                return city
    except Exception:
        pass
    return name


# wttr.in（World Weather Online）的天气代码 → 中文
WWO_ZH = {
    113: "晴", 116: "多云", 119: "阴", 122: "阴天", 143: "薄雾", 248: "雾", 260: "冻雾",
    176: "局部有雨", 179: "局部有雪", 182: "局部雨夹雪", 185: "局部冻毛毛雨",
    200: "局部雷阵雨", 227: "风吹雪", 230: "暴风雪",
    263: "局部小雨", 266: "毛毛雨", 281: "冻毛毛雨", 284: "强冻毛毛雨",
    293: "局部小雨", 296: "小雨", 299: "间中中雨", 302: "中雨",
    305: "间中大雨", 308: "大雨", 311: "小冻雨", 314: "中到大冻雨",
    317: "小雨夹雪", 320: "中到大雨夹雪",
    323: "局部小雪", 326: "小雪", 329: "局部中雪", 332: "中雪",
    335: "局部大雪", 338: "大雪", 350: "冰粒",
    353: "小阵雨", 356: "中到大阵雨", 359: "暴雨",
    362: "小阵雨夹雪", 365: "中到大阵雨夹雪",
    368: "小阵雪", 371: "中到大阵雪", 374: "小冰粒阵", 377: "中到大冰粒阵",
    386: "局部雷阵雨", 389: "雷阵雨", 392: "局部雷阵雪", 395: "雷阵雪",
}


def en_weather_to_zh(raw):
    """英文天气描述兜底翻译（认不出来就返回中文的"未知"，绝不吐英文）。"""
    t = (raw or "").lower()
    if "thunder" in t:
        return "雷阵雪" if "snow" in t else "雷阵雨"
    if "blizzard" in t or "blowing snow" in t:
        return "暴风雪"
    if "snow" in t:
        if "heavy" in t:
            return "大雪"
        if "moderate" in t:
            return "中雪"
        return "小雪"
    if "sleet" in t or "ice pellet" in t or "ice pellets" in t:
        return "雨夹雪"
    if "freezing" in t and "rain" in t:
        return "冻雨"
    if "drizzle" in t:
        return "毛毛雨"
    if "rain" in t or "shower" in t:
        if "torrential" in t or "heavy" in t:
            return "大雨"
        if "moderate" in t:
            return "中雨"
        return "小雨"
    if "freezing fog" in t:
        return "冻雾"
    if "fog" in t:
        return "雾"
    if "mist" in t or "haze" in t:
        return "薄雾"
    if "overcast" in t:
        return "阴天"
    if "cloud" in t:
        return "多云" if ("partly" in t or "patchy" in t) else "阴"
    if "sunny" in t or "clear" in t:
        return "晴"
    if "wind" in t:
        return "大风"
    return "未知天气"


def weather_desc_zh(cur):
    """把 wttr.in 的 current_condition 翻成中文描述：优先用天气代码，再退回英文关键词。"""
    code = cur.get("weatherCode")
    try:
        code = int(code)
    except (TypeError, ValueError):
        code = None
    if code in WWO_ZH:
        return WWO_ZH[code]
    desc = ""
    try:
        desc = (cur.get("weatherDesc") or [{}])[0].get("value", "")
    except Exception:
        desc = ""
    return en_weather_to_zh(desc)


# open-meteo（WMO）天气代码 → 中文，作为 wttr.in 的备用数据源
WMO_ZH = {
    0: "晴", 1: "晴间多云", 2: "多云", 3: "阴", 45: "雾", 48: "冻雾",
    51: "小毛毛雨", 53: "毛毛雨", 55: "大毛毛雨", 56: "冻毛毛雨", 57: "强冻毛毛雨",
    61: "小雨", 63: "中雨", 65: "大雨", 66: "冻雨", 67: "强冻雨",
    71: "小雪", 73: "中雪", 75: "大雪", 77: "雪粒",
    80: "小阵雨", 81: "中阵雨", 82: "强阵雨", 85: "小阵雪", 86: "大阵雪",
    95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
}


def fetch_weather(city):
    """查天气：先问 wttr.in（带重试），不行就用 open-meteo 兜底。

    返回 (温度, 中文描述)；都失败返回 None。
    """
    for attempt in range(2):
        try:
            r = requests.get(f"https://wttr.in/{city}?format=j1", timeout=12,
                             headers={"User-Agent": "Mozilla/5.0"})
            cur = (r.json() or {})["current_condition"][0]
            return cur["temp_C"], weather_desc_zh(cur)
        except Exception:
            if attempt == 0:
                time.sleep(0.6)
    try:
        g = requests.get("https://geocoding-api.open-meteo.com/v1/search",
                         params={"name": city, "count": 1, "language": "zh"},
                         timeout=10).json() or {}
        found = g.get("results") or []
        if found:
            w = requests.get("https://api.open-meteo.com/v1/forecast",
                             params={"latitude": found[0]["latitude"],
                                     "longitude": found[0]["longitude"],
                                     "current": "temperature_2m,weather_code"},
                             timeout=10).json() or {}
            cur = w.get("current") or {}
            if cur.get("temperature_2m") is not None:
                code = cur.get("weather_code")
                desc = WMO_ZH.get(int(code), "未知天气") if code is not None else "未知天气"
                return str(round(float(cur["temperature_2m"]))), desc
    except Exception:
        pass
    return None


def record_balance_usage(path, total, currency):
    """小鲸鱼记账：只把余额下降记成当日消耗，跨天归零归档，币种变化只重置基准。"""
    today = datetime.now().strftime("%Y-%m-%d")
    data = {"date": today, "lastBalance": total, "lastCurrency": currency,
            "todayUsage": 0.0, "history": {}}
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data.update(json.load(f) or {})
    except Exception:
        pass

    if data.get("date") != today:
        hist = dict(data.get("history") or {})
        if data.get("date") and data.get("todayUsage"):
            hist[data["date"]] = round(float(data["todayUsage"]), 4)
        hist = dict(sorted(hist.items())[-30:])
        data = {"date": today, "lastBalance": total, "lastCurrency": currency,
                "todayUsage": 0.0, "history": hist}
    else:
        last, last_cur = data.get("lastBalance"), data.get("lastCurrency")
        if last is not None and last_cur == currency:
            delta = float(last) - float(total)
            if delta > 0:
                data["todayUsage"] = round(float(data.get("todayUsage") or 0) + delta, 4)
        data["lastBalance"] = total
        data["lastCurrency"] = currency

    data["updatedAt"] = datetime.now().isoformat(timespec="seconds")
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return float(data.get("todayUsage") or 0)


def load_json(path, default):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump(
                default,
                f,
                ensure_ascii=False,
                indent=4
            )
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


class PetWindow(QWidget):
    # ---------- 城市（联网添加） ----------
    def auto_locate_city(self):
        """按 IP 联网定位城市（挂梯子时定位到的是节点所在地）。"""
        self.say("我联网找找你在哪…")
        threading.Thread(target=lambda: self._city_queue.append(to_chinese_city(locate_city_by_ip())),
                         daemon=True).start()

    def search_city_dialog(self):
        """联网搜索城市：先查地理编码，查不到就用天气接口验证这个名字能不能用。"""
        with self._ui_guard():
            name, ok = QInputDialog.getText(self, "添加城市", "输入城市名（联网搜索）:",
                                            QLineEdit.EchoMode.Normal, "",
                                            Qt.WindowType.WindowStaysOnTopHint)
        if not ok or not name.strip():
            return
        self.say("查一下这个城市…")
        threading.Thread(target=lambda: self._city_pick_queue.append(lookup_city(name)),
                         daemon=True).start()

    def _apply_city(self, name):
        self.cfg["city"] = name
        self.save_config()              # 立刻落盘，下次启动就是这个默认城市
        self.say(f"城市已设置为{name}")
        self._get_weather()

    def set_city_dialog(self):
        """手动设置默认城市：直接写进 config.json，不联网、不用等搜索。"""
        with self._ui_guard():
            city, ok = QInputDialog.getText(
                self,
                "设置默认城市",
                "输入城市名（中文英文都行，例如：汕头 / Shantou）:",
                QLineEdit.EchoMode.Normal,
                self.cfg.get("city", "汕头"),
                Qt.WindowType.WindowStaysOnTopHint
            )
        if ok and city.strip():
            self._apply_city(city.strip())
        elif ok:
            self.say("城市名不能为空")

    # ---------- 配置 ----------
    def save_config(self):
        """把当前配置写回 config.json。"""
        try:
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
            self._cfg_snapshot = json.dumps(self.cfg, ensure_ascii=False, sort_keys=True)
        except Exception as ex:
            print("配置保存失败:", repr(ex))

    def autosave_config(self):
        """配置有变化就顺手存一下，不用等到退出（被杀掉也不丢设置）。"""
        try:
            now_snap = json.dumps(self.cfg, ensure_ascii=False, sort_keys=True)
        except Exception:
            return
        if now_snap != getattr(self, "_cfg_snapshot", None):
            self.save_config()

    def __init__(self):
        # 默认配置；老 config.json 缺的新键会自动补上（免得升级后 KeyError）
        cfg_defaults = {
            "mode": "wander",
            "size": 0.7,
            "topmost": True,
            "passthrough": False,
            "autostart": False,
            "x": None,
            "y": None,
            "ds_api_key": "",
            "city": "汕头",
            "balance_always": False,
            "snap_on": True,
            "flip_on_left": True,
            "turn_cost_on": True,
            "skin": SKIN_PET,
            "sound_on": True,
            "sound_set": "小黄鸭",
            "volume": 0.9,
            "show_peak": True,
            "peak_style": "默认",
            "layer": "top",
            "opacity": 1.0,
            "process_alerts": True,
            "custom_skins": {},
            "balance_source": "DeepSeek",
            "other_keys": [],
            "codex_sessions_dir": CODEX_SESSIONS_DIR
        }
        self.cfg = load_json(CONFIG_PATH, dict(cfg_defaults))
        for cfg_key, cfg_value in cfg_defaults.items():
            self.cfg.setdefault(cfg_key, cfg_value)
        self._cfg_snapshot = None
        
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool
        if self.cfg.get("topmost", True):
            flags |= Qt.WindowType.WindowStaysOnTopHint
        super().__init__(None, flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowTitle("大肥鱼桌宠")
        
        # 精灵加载（三视图 + 挂件，每一张都可以被用户自定义图片替换）
        self.sprites = {}
        self.custom_skin_ok = {}
        self._rebuild_sprites()
        self.icon = QIcon(os.path.join(SPRITE_DIR, "icon.png"))

        self.skin = self.cfg.get("skin", SKIN_PET)
        if self.skin not in (SKIN_PET, SKIN_WIDGET) or (self.skin == SKIN_WIDGET
                                                        and not self._has_sprite("挂件")):
            self.skin = SKIN_PET

        self.cur_h = int(340 * self.cfg["size"])
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)

        # 状态
        self.mode = self.cfg["mode"] if self.cfg["mode"] in ("wander", "follow", "still") else "wander"
        self.dir = "down"
        self.facing = 1
        self.target = None
        self.rest_until = 0
        self.cur_speed = 0.0
        self.prev_key = None
        self.cross_t = 0.0
        self.action = None
        self.action_t = 0.0
        self.bubble_text = ""
        self.bubble_until = 0
        self.bubble_inner = False
        self.last_speak_tick = 0
        self.t = 0
        self.jump_t = 0
        self.dragging = False
        self.drag_offset = None
        self.drag_start_pos = None
        self.last_line = ""
        self.last_press_pos = None

        # 余额挂件状态
        self.balance = None          # {"total": 24.05, "currency": "CNY", "today": 0.0, "stale": False}
        self.bal_until = 0.0         # 余额泡泡显示截止时间（秒）
        self.balance_always = bool(self.cfg.get("balance_always", False))
        self.show_peak = bool(self.cfg.get("show_peak", True))
        self.peak_style = self.cfg.get("peak_style", "默认")
        if self.peak_style not in PEAK_TEXT_STYLES:
            self.peak_style = "默认"
        self._peak_now = None
        self.layer = self.cfg.get("layer", "top")
        if self.layer not in ("top", "bottom", "normal"):
            self.layer = "top"
        self.opacity = float(self.cfg.get("opacity", 1.0) or 1.0)
        self.process_alerts = bool(self.cfg.get("process_alerts", True))
        self._running_procs = None      # 第一次扫描只记录，不冒泡
        self._last_proc_say = 0.0
        self._foreground_proc = None     # 上一次的前台应用
        self._proc_said_at = {}          # 每个应用上次吐槽的时间
        self._last_pos = (0, 0)          # 卡住自检用
        self._stuck_ticks = 0
        self.snap_on = bool(self.cfg.get("snap_on", True))
        self.flip_on_left = bool(self.cfg.get("flip_on_left", True))
        self.turn_cost_on = bool(self.cfg.get("turn_cost_on", True))
        self.bal_busy = False
        self.bal_error = ""
        self._bal_queue = []         # 后台线程 → 主线程的余额结果
        self._pending_bubbles = []   # [(到点秒, 文本, 是否心声)]
        self.roll_shown = None       # 数字滚动当前值
        self.roll_from = None
        self.roll_to = None
        self.roll_t = 1.0
        self.press_t = 0.0           # 按压 Q 弹
        self.flip_x = False          # 整体水平翻转（左吸附）
        self.snap_h = None           # 吸附锚点：left / right
        self.snap_v = None           # top / bottom
        self.ui_open = False         # 右键菜单 / 对话框开着时，桌宠站住不动

        # 音效
        self.sound_on = bool(self.cfg.get("sound_on", True))
        self.sound_set = self.cfg.get("sound_set", "小黄鸭")
        self.volume = float(self.cfg.get("volume", 0.9))
        self._sounds = {}
        self._sound_idx = {}
        self._pending_sounds = []
        self._click_clips = pick_click_clips()
        # 常开音频流（首选）：设备一直是醒的，点下去立刻出声、开头不会被吞
        self._click_player = None
        if AUDIO_AVAILABLE:
            player = ClickPlayer(self)
            if player.ok:
                for clip_name, clip_path in self._click_clips.items():
                    player.load_clip(clip_name, clip_path)
                self._click_player = player
            else:
                player.deleteLater()
        self._init_sounds()
        
        # 后台线程 → 主线程的结果队列
        self._say_queue = []          # 要冒泡的文本
        self._city_queue = []         # 自动定位结果
        self._city_pick_queue = []    # 城市搜索候选

        # 每轮 Codex 对话消耗（读 Codex 会话日志的 token 用量）
        self.codex_dir = self.cfg.get("codex_sessions_dir", CODEX_SESSIONS_DIR)
        self._codex_file = None
        self._codex_pos = 0
        self._codex_turn = None
        self._codex_tokens = {}
        self._codex_reported = set()
        self._codex_last_change = 0.0
        self.cdx_timer = QTimer(self)
        self.cdx_timer.timeout.connect(self.scan_codex_usage)
        self.cdx_timer.start(CODEX_SCAN_MS)

        # 有些窗口（比如 Codex）自己也置顶，会盖住桌宠：定期把自己顶到置顶层最前面（不抢焦点）
        self.top_timer = QTimer(self)
        self.top_timer.timeout.connect(self._keep_on_top)
        self.top_timer.start(2000)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(TICK)

        # 余额：60 秒自动刷新 + 启动后先取一次
        self.bal_timer = QTimer(self)
        self.bal_timer.timeout.connect(lambda: self.refresh_balance(silent=True))
        self.bal_timer.start(BALANCE_TTL * 1000)
        QTimer.singleShot(1200, lambda: self.refresh_balance(silent=False))

        self.bubble_font = QFont("Microsoft YaHei UI", 11)

        # 托盘
        self.tray = QSystemTrayIcon(self.icon, self)
        self.tray.setContextMenu(self._make_menu())
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

        x, y = self.cfg.get("x"), self.cfg.get("y")
        if x is None or y is None:
            screen = QApplication.primaryScreen().availableGeometry()
            x = screen.right() - self.width() - 80
            y = screen.bottom() - self.height() - 60
        self.move(int(x), int(y))
        self.show()
        self.snap_into_screen()
        QTimer.singleShot(1500, self.warm_up_sounds)   # 音频设备预热，消掉首次点击的延迟
        self.setWindowOpacity(self.opacity)
        QTimer.singleShot(300, self._apply_layer)       # 层级要在窗口真正显示之后再摆
        if self.cfg.get("passthrough", False):
            self._apply_passthrough(True)

        # 进程联动：打开某些应用时冒个泡
        self.proc_timer = QTimer(self)
        self.proc_timer.timeout.connect(self.check_processes)
        self.proc_timer.start(2000)

    # ---------- 余额 ----------
    def _api_key(self):
        """优先用配置里的 Key，其次用系统环境变量 DEEPSEEK_API_KEY。"""
        return (self.cfg.get("ds_api_key") or os.environ.get("DEEPSEEK_API_KEY", "") or "").strip()

    def _current_source(self):
        """当前余额来源 → (显示名, key)。"""
        name = self.cfg.get("balance_source") or "DeepSeek"
        if name != "DeepSeek":
            for item in (self.cfg.get("other_keys") or []):
                if item.get("name") == name:
                    return name, (item.get("key") or "").strip()
        return "DeepSeek", self._api_key()

    def refresh_balance(self, silent=True):
        """后台拉余额，结果丢进 _bal_queue 由主线程处理（Qt 界面只在主线程更新）。"""
        name, key = self._current_source()
        if not key:
            self.bal_error = f"未配置 {name} 的 Key"
            if not silent:
                self.say(f"先在右键菜单里设置 {name} 的 Key 吧！")
            return
        if self.bal_busy:
            return
        self.bal_busy = True

        def worker():
            low = name.lower()
            if low.startswith("deepseek"):
                res = query_deepseek_balance(key)
            elif "openrouter" in low:
                res = query_openrouter_balance(key)
            else:
                # OpenAI / ChatGPT 这类：官方没开放余额接口，如实告诉用户
                res = {"ok": False, "code": "NO_API",
                       "error": f"{name} 没有提供余额查询接口，看不到具体余额"}
            res["name"] = name
            res["silent"] = silent
            self._bal_queue.append(res)

        threading.Thread(target=worker, daemon=True).start()

    def _apply_balance(self, res):
        self.bal_busy = False
        if not res.get("ok"):
            self.bal_error = str(res.get("error") or "")
            if res.get("code") == "NO_API":
                # 这个服务压根没有余额接口：不报错，如实展示
                self.balance = {"name": res.get("name") or "?", "total": None,
                                "currency": "", "today": 0.0, "no_api": True}
                self.show_balance_bubble(8.0)
                return
            if not res.get("silent") and self.balance is None:
                self.say("余额取不到：" + self.bal_error[:14])
            return

        total, currency = float(res["total"]), res["currency"]
        name = res.get("name") or "DeepSeek"
        # 今日已用记账只对 DeepSeek 有意义（本地按余额差值记账）
        today = record_balance_usage(USAGE_PATH, total, currency) if name == "DeepSeek" else 0.0
        old = self.balance["total"] if self.balance else None
        self.balance = {"name": name, "total": total, "currency": currency,
                        "today": today, "stale": False, "no_api": False}
        self.bal_error = ""
        self._start_roll(total)

        if not res.get("silent"):
            self.show_balance_bubble(6.0)
        elif old is None or abs(total - old) > 1e-9:
            # 余额变了就滚一次给主人看
            self.show_balance_bubble(4.0)

    def _start_roll(self, target):
        """余额变化时从旧值滚到新值。"""
        if self.roll_shown is None:
            self.roll_shown = float(target)
            self.roll_t = 1.0
            return
        if abs(float(target) - float(self.roll_shown)) < 1e-9:
            self.roll_t = 1.0
            return
        self.roll_from = float(self.roll_shown)
        self.roll_to = float(target)
        self.roll_t = 0.0

    def _display_amount(self):
        if self.balance is None:
            return 0.0
        if self.balance.get("total") is None:
            return 0.0
        if self.roll_shown is None or self.roll_t >= 1.0:
            return float(self.balance["total"])
        eased = 1 - (1 - self.roll_t) ** 3
        return self.roll_from + (self.roll_to - self.roll_from) * eased

    def show_balance_bubble(self, seconds=6.0):
        self.bal_until = self.t * TICK / 1000.0 + seconds
        # 收起普通气泡，避免两层叠在一起
        self.bubble_text = ""
        self.bubble_until = 0.0
        self.update()

    def _say_later(self, seconds, text, inner=False):
        self._pending_bubbles.append((self.t * TICK / 1000.0 + seconds, text, inner))

    # ---------- 音效 / 形象 ----------
    @staticmethod
    def _crop_alpha(pix):
        """裁掉四周全透明空白（逐行扫描 alpha，避免逐像素 Python 调用）。"""
        img = pix.toImage().convertToFormat(QImage.Format.Format_ARGB32)
        w, h = img.width(), img.height()
        data = bytes(img.constBits())
        bpl = img.bytesPerLine()
        minx, miny, maxx, maxy = w, h, -1, -1
        for y in range(h):
            alphas = data[y * bpl: y * bpl + w * 4][3::4]
            if max(alphas) <= 8:
                continue
            x = 0
            while alphas[x] <= 8:
                x += 1
            x2 = w - 1
            while alphas[x2] <= 8:
                x2 -= 1
            minx, maxx = min(minx, x), max(maxx, x2)
            miny, maxy = min(miny, y), y
        if maxx < 0:
            return pix
        return pix.copy(minx, miny, maxx - minx + 1, maxy - miny + 1)

    def _init_sounds(self):
        """为每套音效准备多个播放实例。

        一次点击只播一声完整音效，不再区分按压/松手；多实例是为了连点时互不打断；
        没解码好的实例会先登记，等 Ready 立刻补播（避免「点了没声音」）。
        """
        if not AUDIO_AVAILABLE:
            return
        for name, clip in self._click_clips.items():
            url = QUrl.fromLocalFile(clip)
            instances = []
            for _ in range(SOUND_POOL):
                eff = QSoundEffect(self)
                eff.setSource(url)
                eff.setVolume(self.volume)
                instances.append(eff)
            self._sounds[name] = instances

    def play_click(self):
        """点一下播一声完整音效；池里轮着用，连点就按点击间隔自然响。"""
        if not self.sound_on:
            return
        if self.sound_set in self._click_clips:
            name = self.sound_set
        else:
            name = "小黄鸭"
        if self._click_player and self._click_player.has_clip(name):
            self._click_player.volume = self.volume
            self._click_player.play(name)
            return
        pool = self._sounds.get(name)
        if not pool:
            self._play_fallback_click()
            return
        idx = self._sound_idx.get(name, 0)
        eff = pool[idx % len(pool)]
        self._sound_idx[name] = (idx + 1) % len(pool)
        if eff.source().isEmpty():
            return
        try:
            eff.setVolume(self.volume)
            if eff.status() == QSoundEffect.Status.Ready:
                eff.play()
            else:
                # 还没解码好：先记下，等 Ready 立刻补播（比直接丢音好）
                self._pending_sounds.append((eff, time.time()))
        except Exception:
            pass

    def _flush_pending_sounds(self):
        if not self._pending_sounds:
            return
        now = time.time()
        keep = []
        for eff, ts in self._pending_sounds:
            if eff.status() == QSoundEffect.Status.Ready:
                try:
                    eff.setVolume(self.volume)
                    eff.play()
                except Exception:
                    pass
            elif now - ts < 1.5:      # 太久了就别补了，免得突然冒出来
                keep.append((eff, ts))
        self._pending_sounds = keep

    def warm_up_sounds(self):
        """启动后把音频设备先唤醒（0 音量静音放一遍），消掉第一次点击的延迟。"""
        if self._click_player:
            return                      # 常开流本来就在跑，不用预热
        for instances in self._sounds.values():
            for eff in instances:
                if eff.status() != QSoundEffect.Status.Ready:
                    continue
                try:
                    eff.setVolume(0.0)
                    eff.play()
                except Exception:
                    pass
        QTimer.singleShot(600, self._restore_sound_volume)

    def _restore_sound_volume(self):
        for instances in self._sounds.values():
            for eff in instances:
                eff.setVolume(self.volume)

    def preview_sounds(self):
        """试听当前这套点击音效。"""
        self.play_click()

    def _play_fallback_click(self):
        """Qt 音频不可用时的兜底：用系统 winsound 异步播 wav（没有音量控制）。"""
        try:
            import winsound
            name = self.sound_set if self.sound_set in self._click_clips else "小黄鸭"
            path = self._click_clips.get(name)
            if path and os.path.exists(path):
                winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC
                                   | winsound.SND_NODEFAULT)
        except Exception:
            pass

    def set_sound(self, on):
        self.sound_on = bool(on)
        self.cfg["sound_on"] = bool(on)

    def set_sound_set(self, name):
        if name not in SOUND_SETS:
            return
        self.sound_set = name
        self.cfg["sound_set"] = name
        self.play_click()          # 换音效顺手试听一声

    def set_volume(self, vol):
        self.volume = max(0.0, min(1.0, float(vol)))
        self.cfg["volume"] = self.volume
        if self._click_player:
            self._click_player.volume = self.volume
        self._restore_sound_volume()

    # ---------- 形象加载 ----------
    def _custom_path(self, view):
        """该视图用户自定义的图片路径（不存在就返回空）。"""
        path = (self.cfg.get("custom_skins") or {}).get(view) or ""
        return path if path and os.path.exists(path) else ""

    def _has_sprite(self, key):
        return any(k[0] == key for k in self.sprites)

    def _load_view_pixmap(self, view, h):
        """加载某个视图的某个高度：优先用户自定义图片，其次自带素材。"""
        custom = self._custom_path(view)
        if custom:
            pix = QPixmap(custom)
            if not pix.isNull():
                self.custom_skin_ok[view] = True
                return self._crop_alpha(pix).scaledToHeight(
                    h, Qt.TransformationMode.SmoothTransformation)
        self.custom_skin_ok[view] = False
        if view == "widget":
            base = QPixmap(os.path.join(ASSET_DIR, WIDGET_SKIN_FILE))
            if base.isNull():
                return None
            return self._crop_alpha(base).scaledToHeight(
                h, Qt.TransformationMode.SmoothTransformation)
        name = SPRITE_VIEWS[view]
        sized = os.path.join(SPRITE_DIR, f"{name}_{h}.png")
        if os.path.exists(sized):
            return QPixmap(sized)
        full = os.path.join(SPRITE_DIR, f"{name}.png")
        if not os.path.exists(full):
            return None
        return QPixmap(full).scaledToHeight(h, Qt.TransformationMode.SmoothTransformation)

    def _rebuild_sprites(self):
        """重新加载各尺寸精灵（换了自定义图片后调用）。"""
        sprite_key = {"front": "正面", "side": "侧面", "back": "背面", "widget": "挂件"}
        self.sprites = {}
        for _label, mult in SIZE_LEVELS.items():
            h = int(340 * mult)
            for view, key in sprite_key.items():
                pix = self._load_view_pixmap(view, h)
                if pix is not None and not pix.isNull():
                    self.sprites[(key, h)] = pix
        self.widget_skin_ok = self._has_sprite("挂件")

    def pick_custom_skin(self, view):
        """让用户挑一张图片当作某个视图的形象。"""
        label = VIEW_LABELS.get(view, view)
        with self._ui_guard():
            path, _ok = QFileDialog.getOpenFileName(
                self, f"选择{label}的图片", os.path.expanduser("~"),
                "图片 (*.png *.jpg *.jpeg *.webp *.bmp *.gif)",
                options=QFileDialog.Option.DontUseNativeDialog)
        if not path:
            return
        if QPixmap(path).isNull():
            self.say("这张图读不了，换一张试试")
            return
        skins = dict(self.cfg.get("custom_skins") or {})
        skins[view] = path
        self.cfg["custom_skins"] = skins
        self._rebuild_sprites()
        self.set_size(self.cfg.get("size", 0.7))
        self.save_config()
        self.say(f"{label}换成你自己的图啦")

    def clear_custom_skin(self, view=None):
        """恢复默认形象（只清某一个视图，或全清）。"""
        skins = dict(self.cfg.get("custom_skins") or {})
        if view:
            skins.pop(view, None)
        else:
            skins = {}
        self.cfg["custom_skins"] = skins
        self._rebuild_sprites()
        if self.skin == SKIN_WIDGET and not self._has_sprite("挂件"):
            self.skin = SKIN_PET
            self.cfg["skin"] = SKIN_PET
        self.set_size(self.cfg.get("size", 0.7))
        self.save_config()
        self.say("已恢复自带形象")

    def set_skin(self, name):
        """切换形象：大肥鱼（三视图）/ 小鲸鱼挂件（单张）。"""
        if name == SKIN_WIDGET and not self.widget_skin_ok:
            self.say("小鲸鱼形象没找到图片")
            return
        self.skin = name
        self.cfg["skin"] = name
        self.prev_key = None
        self.cross_t = 0.0
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(p.width() for k, p in self.sprites.items()
                         if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)
        self._settle()
        self.update()

    # ---------- 吸附 / 翻转 ----------
    def _snap_to_edge(self):
        """松手后按四分之一区域吸附屏幕四边（角落可组合），左吸附时整体水平翻转。"""
        if not self.snap_on:
            self.snap_h = self.snap_v = None
            self.flip_x = False
            return
        geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        cx, cy = self.x() + self.width() / 2, self.y() + self.height() / 2
        self.snap_h = ("left" if cx < geo.left() + geo.width() / 4
                       else "right" if cx > geo.right() - geo.width() / 4 else None)
        self.snap_v = ("top" if cy < geo.top() + geo.height() / 4
                       else "bottom" if cy > geo.bottom() - geo.height() / 4 else None)
        self._settle(geo)

    def _settle(self, geo=None):
        if not self.snap_on or (self.snap_h is None and self.snap_v is None):
            return
        geo = geo or (self.screen() or QApplication.primaryScreen()).availableGeometry()
        x, y = self.x(), self.y()
        if self.snap_h == "left":
            x = geo.left()
        elif self.snap_h == "right":
            x = geo.right() - self.width() + 1
        if self.snap_v == "top":
            y = geo.top()
        elif self.snap_v == "bottom":
            y = geo.bottom() - self.height() + 1
        # 吸附轴已经是精确贴边，只有没吸附的轴才需要钳制在屏幕内
        if self.snap_h is None:
            x = max(geo.left(), min(geo.right() - self.width(), x))
        if self.snap_v is None:
            y = max(geo.top(), min(geo.bottom() - self.height(), y))
        self.flip_x = bool(self.flip_on_left and self.snap_h == "left")
        self.move(int(x), int(y))

    # ---------- 绘制 ----------
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        now = self.t * TICK / 1000.0

        show_balance = self.balance is not None and (self.balance_always or now < self.bal_until)
        if self.bubble_text and now < self.bubble_until:
            if self.bubble_inner:
                bfont = QFont(self.bubble_font)
                bfont.setItalic(True)
                bg, fg = QColor(232, 232, 238, 242), QColor(125, 125, 138)
            else:
                bfont = QFont(self.bubble_font)
                bg, fg = QColor(255, 255, 255, 242), QColor(60, 60, 80)
            fm = QFontMetrics(bfont)
            max_w = min(240, self.width() - 16)
            words = self.bubble_text
            lines = []
            cur = ""
            for ch in words:
                if fm.horizontalAdvance(cur + ch) > max_w - 20:
                    lines.append(cur)
                    cur = ch
                else:
                    cur += ch
            lines.append(cur)
            bw = max(fm.horizontalAdvance(l) for l in lines) + 28
            bh = len(lines) * fm.height() + 16
            bx = (self.width() - bw) / 2
            by = self._bubble_top(bh)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(bg)
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 14, 14)
            tail = QPointF(self.width() / 2, by + bh)
            p.drawPolygon(QPolygonF([tail, QPointF(tail.x() - 7, tail.y() + 9),
                                     QPointF(tail.x() + 7, tail.y() + 9)]))
            p.setPen(fg)
            p.setFont(bfont)
            for i, l in enumerate(lines):
                p.drawText(QRectF(bx, by + 8 + i * fm.height(), bw, fm.height()),
                           Qt.AlignmentFlag.AlignCenter, l)
        elif show_balance:
            # 余额气泡：余额 / 今日已用（数字带滚动动画）
            f_small = QFont(self.bubble_font)
            f_small.setPointSize(9)
            f_big = QFont(self.bubble_font)
            f_big.setPointSize(15)
            f_big.setBold(True)
            fm_s, fm_b = QFontMetrics(f_small), QFontMetrics(f_big)
            src = self.balance.get("name") or "DeepSeek"
            symbol = currency_symbol(self.balance.get("currency"))
            peak_now = is_peak()
            show_peak_line = bool(self.show_peak and src == "DeepSeek")
            if self.balance.get("no_api"):
                # 这个服务不提供余额接口，直接说清楚
                l1 = src
                l2 = "无法查询"
                l3 = "该服务不提供余额接口"
                show_peak_line = False
            else:
                l1 = f"{src} 余额"
                l2 = f"{symbol} {self._display_amount():.2f}".strip()
                l3 = (f"今日已用 {symbol} {self.balance['today']:.2f}".strip()
                      if src == "DeepSeek" else "今日已用 仅 DeepSeek 支持")
            l4 = f"现在 {peak_label(peak_now, self.peak_style)}"
            bw = max(fm_b.horizontalAdvance(l2), fm_s.horizontalAdvance(l1),
                     fm_s.horizontalAdvance(l3), fm_s.horizontalAdvance(l4)) + 28
            bh = fm_s.height() + fm_b.height() + fm_s.height() + 16
            if show_peak_line:
                bh += fm_s.height()
            bx = (self.width() - bw) / 2
            by = self._bubble_top(bh)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(255, 255, 255, 242))
            p.drawRoundedRect(QRectF(bx, by, bw, bh), 14, 14)
            tail = QPointF(self.width() / 2, by + bh)
            p.drawPolygon(QPolygonF([tail, QPointF(tail.x() - 7, tail.y() + 9),
                                     QPointF(tail.x() + 7, tail.y() + 9)]))
            ty = by + 8
            p.setFont(f_small)
            p.setPen(QColor(130, 138, 158))
            p.drawText(QRectF(bx, ty, bw, fm_s.height()), Qt.AlignmentFlag.AlignCenter, l1)
            ty += fm_s.height()
            p.setFont(f_big)
            p.setPen(QColor(32, 49, 112))
            p.drawText(QRectF(bx, ty, bw, fm_b.height()), Qt.AlignmentFlag.AlignCenter, l2)
            ty += fm_b.height()
            p.setFont(f_small)
            p.setPen(QColor(150, 150, 165))
            p.drawText(QRectF(bx, ty, bw, fm_s.height()), Qt.AlignmentFlag.AlignCenter, l3)
            if show_peak_line:
                ty += fm_s.height()
                p.setFont(f_small)
                # 高峰暖色、空闲绿色，一眼看出现在贵不贵
                p.setPen(QColor(198, 90, 20) if peak_now else QColor(46, 125, 50))
                p.drawText(QRectF(bx, ty, bw, fm_s.height()), Qt.AlignmentFlag.AlignCenter, l4)

        cx = self.width() / 2
        walking = self.target is not None and not self.dragging
        if walking:
            sway = math.sin(now * 9.0) * 3.5
            bob = -abs(math.sin(now * 4.5)) * 7.0
        else:
            sway = math.sin(now * 2.5) * 1.5
            bob = 0.0
        breath = 1.0 + 0.02 * math.sin(now * 2.5)
        scale = breath
        jump = -abs(math.sin(self.jump_t * 3.14159)) * 14 * self.jump_t if self.jump_t > 0 else 0
        act_rot = act_sx = act_sy = 0.0
        if self.action == "sway":
            act_rot = math.sin(self.action_t * 3.14159 * 2) * 10 * self.action_t
        elif self.action == "stretch":
            act_sy = 0.06 * math.sin(self.action_t * 3.14159)
            act_sx = -0.03 * math.sin(self.action_t * 3.14159)

        # 按压 Q 弹：底部坐标不变，横向撑开、纵向压扁
        press_sx = 1 + 0.13 * self.press_t
        press_sy = 1 - 0.13 * self.press_t

        def draw_one(key, opacity):
            if key is None:
                return
            name, h, facing = key
            pix = self.sprites[(name, h)]
            ph = pix.height() * scale * (1 + act_sy) * press_sy
            pw = pix.width() * scale * (1 + act_sx) * press_sx
            dx = cx - pw / 2
            bottom = BUBBLE_H + MARGIN + self.cur_h
            dy = bottom - ph + jump + bob
            p.save()
            p.setOpacity(opacity)
            p.translate(cx, bottom)
            p.rotate(sway + act_rot)
            p.translate(-cx, -bottom)
            # 行走朝向 与 左吸附整体翻转 叠加（异或）
            if (facing < 0) != bool(self.flip_x):
                p.translate(cx, 0)
                p.scale(-1, 1)
                p.translate(-cx, 0)
            p.drawPixmap(QRectF(dx, dy, pw, ph), pix, QRectF(0, 0, pix.width(), pix.height()))
            p.restore()

        cur_key = self._sprite_key()
        if self.cross_t > 0:
            draw_one(self.prev_key, self.cross_t)
            draw_one(cur_key, 1.0 - self.cross_t)
        else:
            draw_one(cur_key, 1.0)

    def _bubble_top(self, bh):
        """气泡贴着鱼头顶：尾巴尖落在精灵上沿附近。"""
        return max(2.0, BUBBLE_H + MARGIN - 10 - bh)

    def _sprite_key(self):
        if self.skin == SKIN_WIDGET:
            return ("挂件", self.cur_h,
                    self.facing if self.dir in ("left", "right") else 1)
        name = {"left": "侧面", "right": "侧面", "up": "背面", "down": "正面"}[self.dir]
        return (name, self.cur_h, self.facing if self.dir in ("left", "right") else 1)

    def _set_dir(self, d, facing=None):
        if d != self.dir:
            self.prev_key = self._sprite_key()
            self.cross_t = 1.0
            self.dir = d
        if facing is not None and facing != self.facing:
            self.facing = facing

    # ---------- 逻辑 ----------
    def tick(self):
        self.t += 1

        # 大约每 5 秒顺手存一次配置：改了城市/大小/音效这些不用等退出也不会丢
        if self.t % 250 == 0:
            self.autosave_config()

        # 峰谷切换提醒：每秒看一次，跨进新时段就说一声
        if self.t % 50 == 0:
            peak_now = is_peak()
            if self._peak_now is None:
                self._peak_now = peak_now
            elif peak_now != self._peak_now:
                self._peak_now = peak_now
                self.say("进入" + peak_label(peak_now, self.peak_style)
                         + ("，这会儿聊起来贵一点" if peak_now else "，这会儿便宜"))

        # 处理后台线程排队的气泡消息，Qt 界面必须在主线程更新
        if self._say_queue:
            for text in self._say_queue:
                self.say(text)
            self._say_queue.clear()

        # 余额结果（后台线程 → 主线程）
        if self._bal_queue:
            self._apply_balance(self._bal_queue.pop(0))

        # 余额数字滚动 + 按压回弹 + 音效补播
        if self.roll_t < 1.0:
            self.roll_t = min(1.0, self.roll_t + 0.07)
            if self.roll_t >= 1.0 and self.balance:
                self.roll_shown = float(self.balance["total"])
        if self.press_t > 0:
            self.press_t = max(0.0, self.press_t - 0.12)
        self._flush_pending_sounds()

        # 延迟气泡（每轮消耗等）
        if self._pending_bubbles:
            now_s = self.t * TICK / 1000.0
            due = [x for x in self._pending_bubbles if x[0] <= now_s]
            if due:
                self._pending_bubbles = [x for x in self._pending_bubbles if x[0] > now_s]
                _, text, inner = due[0]
                self.say(text, inner=inner)

        # 城市定位 / 搜索结果
        if self._city_queue:
            city = self._city_queue.pop(0)
            if city:
                self._apply_city(city)
            else:
                self.say("没定位到，右键「天气 → 添加城市」搜一个吧")
        if self._city_pick_queue:
            items = self._city_pick_queue.pop(0)
            labels = [x[0] for x in items]
            with self._ui_guard():
                pick, ok = QInputDialog.getItem(self, "选择城市", "选一个城市：", labels,
                                                0, False, Qt.WindowType.WindowStaysOnTopHint)
            if ok and pick:
                self._apply_city(dict(items)[pick])

        if self.jump_t > 0:
            self.jump_t = max(0.0, self.jump_t - 0.06)
        if self.cross_t > 0:
            self.cross_t = max(0.0, self.cross_t - 0.15)
        if self.action_t > 0:
            self.action_t = max(0.0, self.action_t - 0.03)
            if self.action_t == 0:
                self.action = None

        if self.ui_open:        # 菜单 / 对话框开着：站住不动，免得跳上去把设置面板遮住
            self.update()
            return

        if self.dragging:
            self.update()
            return
        now_ms = self.t * TICK

        if self.mode == "follow":
            cursor = self.cursor().pos()
            screen = QApplication.screenAt(cursor) or self.screen() or QApplication.primaryScreen()
            geo = screen.availableGeometry()
            near = (self.x() - 100 <= cursor.x() <= self.x() + self.width() + 100 and
                    self.y() - 100 <= cursor.y() <= self.y() + self.height() + 100)
            if near:
                self.target = None
            else:
                # 目标点按"窗口中心"算，并且夹在可达范围内，否则贴边时会永远够不到
                half_w, half_h = self.width() / 2, self.height() / 2
                tx = max(geo.left() + half_w, min(geo.right() - half_w, cursor.x()))
                ty = max(geo.top() + half_h, min(geo.bottom() - half_h, cursor.y() + 60))
                self.target = (tx, ty)
        elif self.mode == "wander":
            if self.target is None:
                if now_ms < self.rest_until:
                    self._maybe_idle_action()
                    self.update()
                    return
                geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
                # 同样按窗口中心取点，保证这个点在"窗口不出屏"的钳制范围内可达
                half_w, half_h = self.width() / 2, self.height() / 2
                self.target = (random.randint(int(geo.left() + half_w), int(geo.right() - half_w)),
                               random.randint(int(geo.top() + half_h), int(geo.bottom() - half_h)))
        else:
            if self.t % 250 == 0:
                self._look_at_cursor()
            self._maybe_idle_action()
            self.update()
            return

        if self.target is not None:
            # 卡住保护：有目标却几乎没挪窝（比如贴着屏幕边），2 秒就换个目标
            moved = abs(self.x() - self._last_pos[0]) + abs(self.y() - self._last_pos[1])
            self._last_pos = (self.x(), self.y())
            self._stuck_ticks = 0 if moved >= 2 else self._stuck_ticks + 1
            if self._stuck_ticks > 100:
                self._stuck_ticks = 0
                self.target = None
                self.rest_until = self.t * TICK + random.randint(2000, 6000)
                self._set_dir("down")
                self.update()
                return

            cx, cy = self.x() + self.width() / 2, self.y() + self.height() / 2
            dx, dy = self.target[0] - cx, self.target[1] - cy
            dist = (dx * dx + dy * dy) ** 0.5
            if dist < 12:
                self.target = None
                self.rest_until = self.t * TICK + random.randint(8000, 18000)
                self._set_dir("down")
            else:
                step = self.cur_speed * TICK / 1000.0
                nx, ny = cx + dx / dist * step, cy + dy / dist * step
                # 整个窗口都要留在屏幕内，否则气泡会被顶出屏幕
                geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
                mx = max(geo.left(), min(geo.right() - self.width() + 1, int(nx - self.width() / 2)))
                my = max(geo.top(), min(geo.bottom() - self.height() + 1, int(ny - self.height() / 2)))
                self.move(mx, my)
                # 只要横向有明显位移就走侧面（避免"背过身去不转回来"）；
                # 只有几乎笔直向上才给背影，其余默认正面
                if abs(dx) > 4:
                    self._set_dir("left" if dx < 0 else "right", 1 if dx < 0 else -1)
                elif dy < -4:
                    self._set_dir("up")
                else:
                    self._set_dir("down")
            if random.random() < 0.002 and self.jump_t == 0:
                self.jump_t = 0.5
        target_speed = SPEED if self.target is not None else 0.0
        self.cur_speed += (target_speed - self.cur_speed) * 0.3
        self.update()

    def check_processes(self):
        """切到（或刚打开）某个应用时冒一句吐槽。

        改成看"前台窗口"而不是"新出现的进程"：这样已经开着的微信 / 浏览器 /
        QQ 也算数，不会像以前那样只有刚启动的 Steam 会触发。同一个应用
        10 分钟（ChatGPT 15 分钟）只吐槽一次，避免刷屏。
        """
        if not self.process_alerts:
            return
        name = foreground_process_name()
        if not name:
            return
        if name not in PROCESS_LINES:
            self._foreground_proc = name
            return
        if name == self._foreground_proc:
            return
        self._foreground_proc = name
        now = time.time()
        cooldown = 900 if name == "chatgpt.exe" else 600
        if now - self._proc_said_at.get(name, 0) < cooldown:
            return
        self._proc_said_at[name] = now
        self.say(random.choice(PROCESS_LINES[name]))

    def _look_at_cursor(self):
        """原地待着的时候偶尔转头看向鼠标，显得机灵点。"""
        if self.dragging or self.target is not None:
            return
        cursor = self.cursor().pos()
        dx = cursor.x() - (self.x() + self.width() / 2)
        if abs(dx) > 30:
            self._set_dir("left" if dx < 0 else "right", 1 if dx < 0 else -1)
        else:
            self._set_dir("down")

    def _maybe_idle_action(self):
        if random.random() < 0.01:
            pick = random.random()
            if pick < 0.35:
                self.jump_t = 1.0
            elif pick < 0.6:
                self.action, self.action_t = "sway", 1.0
            elif pick < 0.8:
                self.action, self.action_t = "stretch", 1.0
            elif pick < 0.9:
                if self.t - self.last_speak_tick >= 1500:
                    self.last_speak_tick = self.t
                    if pick < 0.82:
                        self.say(random.choice(INNER_LINES), inner=True)
                    else:
                        self.say(random.choice(LINES))

    def _queue_say(self, text):
        """后台线程调用：只入队，由主线程 tick 统一弹出显示（线程安全）"""
        self._say_queue.append(text)

    def say(self, text, inner=False):
        if text == self.last_line and not text.startswith("天气"):
            return
        self.last_line = text
        self.bubble_inner = inner
        self.bubble_text = f"（{text}）" if inner else text
        self.bubble_until = self.t * TICK / 1000.0 + 2.8
        self.update()

    # ---------- 鼠标事件 ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self.press_t = 1.0          # 按压 Q 弹
            self.play_click()           # 点一次响一声完整音效（不再区分松手）
            self.last_press_pos = e.globalPosition().toPoint()
            self.dragging = False
            self.drag_start_pos = e.globalPosition().toPoint()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MouseButton.LeftButton and self.drag_start_pos is not None:
            delta = e.globalPosition().toPoint() - self.drag_start_pos
            if not self.dragging and delta.manhattanLength() > 6:
                self.dragging = True
                self.drag_offset = e.globalPosition().toPoint() - QPoint(self.x(), self.y())
            if self.dragging and self.drag_offset is not None:
                pos = e.globalPosition().toPoint() - self.drag_offset
                self.move(pos)
                if abs(delta.x()) > 10:
                    self._set_dir("left" if delta.x() < 0 else "right", 1 if delta.x() < 0 else -1)
                self.update()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self.dragging:
                self.dragging = False
                self.drag_offset = None
                self.drag_start_pos = None
                self._set_dir("down", 1)
                self.target = None
                self.rest_until = self.t * TICK + random.randint(6000, 14000)
                self._snap_to_edge()    # 松手后吸附到最近的边
                if random.random() < 0.5:
                    self.say(random.choice(DRAG_LINES))
            else:
                self._on_single_click()
            self.last_press_pos = None
            self.drag_start_pos = None

    def _on_single_click(self):
        """单击：蹦跳 + 回嘴 + 顺手刷一下余额。"""
        self.refresh_balance(silent=True)      # 点一下顺手刷新余额
        if random.random() < 0.7:
            self.jump_t = 1.0
        if random.random() < 0.6:
            self.say(random.choice(REACT_LINES))

    def _get_weather(self):
        """联网查天气（后台线程，别卡住桌宠）。"""
        city = self.cfg.get("city", "汕头")

        def worker():
            got = fetch_weather(city)
            if got:
                temp, desc = got
                self._queue_say(f"{city}今天{temp}°，天气{desc}")
            else:
                self._queue_say("天气没查到，等会儿再试试")

        threading.Thread(target=worker, daemon=True).start()

    # ---------- 每轮 Codex 对话消耗 ----------
    def scan_codex_usage(self):
        """尾巴式读最新的 Codex 会话日志，按 turn 汇总 token 用量。"""
        if not self.turn_cost_on:
            return
        newest = None
        try:
            for root, _dirs, files in os.walk(self.codex_dir):
                for fn in files:
                    if not fn.endswith(".jsonl"):
                        continue
                    p = os.path.join(root, fn)
                    try:
                        m = os.path.getmtime(p)
                    except OSError:
                        continue
                    if newest is None or m > newest[0]:
                        newest = (m, p)
        except Exception:
            return
        if not newest:
            return

        path = newest[1]
        if path != self._codex_file:
            # 换文件了：从末尾开始，别把历史轮次当成本轮
            self._codex_file = path
            try:
                self._codex_pos = os.path.getsize(path)
            except OSError:
                self._codex_pos = 0
            self._codex_turn = None
            self._codex_tokens = {}
            return

        try:
            size = os.path.getsize(path)
            if size < self._codex_pos:      # 文件被截断/轮转
                self._codex_pos = 0
            if size > self._codex_pos:
                with open(path, "r", encoding="utf-8", errors="replace") as f:
                    f.seek(self._codex_pos)
                    for line in f:
                        self._ingest_codex_line(line)
                    self._codex_pos = f.tell()
        except OSError:
            return
        self._report_codex_turn()

    def _ingest_codex_line(self, line):
        if '"token_usage_record"' not in line and '"turn_context"' not in line:
            return
        try:
            obj = json.loads(line)
        except Exception:
            return
        payload = obj.get("payload") or {}
        turn = payload.get("turn_id")
        if not turn:
            return
        if turn != self._codex_turn:
            if self._codex_turn:                  # 上一轮结束了
                self._report_codex_turn(force=True)
            self._codex_turn = turn
        usage = payload.get("turn_token_usage") or payload.get("usage")
        if usage:
            prev = self._codex_tokens.get(turn)
            if not prev or (usage.get("total_tokens") or 0) >= (prev.get("total_tokens") or 0):
                self._codex_tokens[turn] = usage      # 累计值：取最大的那份
            else:
                merged = dict(prev)
                for k, v in usage.items():
                    if isinstance(v, (int, float)):
                        merged[k] = (prev.get(k) or 0) + v
                self._codex_tokens[turn] = merged
            self._codex_last_change = time.time()

    def _report_codex_turn(self, force=False):
        turn = self._codex_turn
        if not turn or turn in self._codex_reported:
            return
        if not force and time.time() - self._codex_last_change < CODEX_QUIET_S:
            return
        self._codex_reported.add(turn)
        if len(self._codex_reported) > 50:
            self._codex_reported = set(list(self._codex_reported)[-25:])
        amount, tokens = codex_usage_cost(self._codex_tokens.get(turn))
        if tokens:
            self.say(f"上一轮消耗 ¥{amount:.4f}（{tokens / 1000:.1f}k token）")

    def _build_menu(self):
        m = QMenu(self)
        mode_menu = m.addMenu("模式")
        for label, key in [("自由散步", "wander"), ("跟随鼠标", "follow"), ("原地待着", "still")]:
            a = mode_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.mode == key)
            a.triggered.connect(lambda _, k=key: self.set_mode(k))
        size_menu = m.addMenu("大小")
        for label, mult in SIZE_LEVELS.items():
            a = size_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(abs(self.cur_h - 340 * mult) < 2)
            a.triggered.connect(lambda _, v=mult: self.set_size(v))
        skin_menu = m.addMenu("形象")
        pet_menu = skin_menu.addMenu(f"{SKIN_PET}（三视图）")
        a = pet_menu.addAction("用这个形象")
        a.setCheckable(True)
        a.setChecked(self.skin == SKIN_PET)
        a.triggered.connect(lambda _, n=SKIN_PET: self.set_skin(n))
        pet_menu.addSeparator()
        for view in ("front", "side", "back"):
            custom = self._custom_path(view)
            label = VIEW_LABELS[view] + ("（已自定义）" if custom else "")
            act = pet_menu.addAction("换成我的图片：" + label)
            act.triggered.connect(lambda _, v=view: self.pick_custom_skin(v))
        if any(self._custom_path(v) for v in ("front", "side", "back")):
            pet_menu.addAction("恢复默认三视图", lambda: self.clear_custom_skin(None))
        whale_menu = skin_menu.addMenu(f"{SKIN_WIDGET}（单张）")
        a = whale_menu.addAction("用这个形象")
        a.setCheckable(True)
        a.setChecked(self.skin == SKIN_WIDGET)
        a.triggered.connect(lambda _, n=SKIN_WIDGET: self.set_skin(n))
        whale_menu.addSeparator()
        whale_menu.addAction("换成我的图片：小鲸鱼挂件", lambda: self.pick_custom_skin("widget"))
        if self._custom_path("widget"):
            whale_menu.addAction("恢复默认小鲸鱼", lambda: self.clear_custom_skin("widget"))
        skin_menu.addSeparator()
        skin_menu.addAction("全部恢复默认形象", lambda: self.clear_custom_skin(None))
        layer_menu = m.addMenu("层级")
        for key, label in self.LAYER_LABELS.items():
            a = layer_menu.addAction(label)
            a.setCheckable(True)
            a.setChecked(self.layer == key)
            a.triggered.connect(lambda _, k=key: self.set_layer(k))
        opa_menu = m.addMenu("透明度")
        opa_action = QWidgetAction(opa_menu)
        opa_slider = QSlider(Qt.Orientation.Horizontal)
        opa_slider.setRange(20, 100)
        opa_slider.setValue(int(self.opacity * 100))
        opa_slider.setFixedWidth(130)
        opa_slider.valueChanged.connect(lambda v: self.set_opacity(v / 100.0))
        opa_action.setDefaultWidget(opa_slider)
        opa_menu.addAction(opa_action)
        weather_menu = m.addMenu("天气")
        weather_menu.addAction("设置默认城市（手动输入）", self.set_city_dialog)
        weather_menu.addAction("查看天气", self._get_weather)
        weather_menu.addAction("自动定位城市（按 IP，挂梯子会不准）", self.auto_locate_city)
        weather_menu.addAction("添加城市（联网搜索）", self.search_city_dialog)
        weather_menu.addSeparator()
        weather_menu.addAction(f"当前城市：{self.cfg.get('city', '汕头')}").setEnabled(False)
        bal_menu = m.addMenu("余额")
        bal_menu.addAction("查看余额", lambda: self.refresh_balance(silent=False))
        bal_menu.addAction("设置 Key", self._set_key_dialog)
        src_menu = bal_menu.addMenu("余额来源")
        for name in ["DeepSeek"] + [k.get("name", "?") for k in (self.cfg.get("other_keys") or [])]:
            a = src_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked((self.cfg.get("balance_source") or "DeepSeek") == name)
            a.triggered.connect(lambda _, n=name: self.set_balance_source(n))
        bal_menu.addAction("添加其他 API Key…", self.add_other_key_dialog)
        if self.cfg.get("other_keys"):
            bal_menu.addAction("删除其他 API Key…", self.remove_other_key_dialog)
        bal_menu.addSeparator()
        baa = bal_menu.addAction("余额常显")
        baa.setCheckable(True)
        baa.setChecked(self.balance_always)
        baa.triggered.connect(self.set_balance_always)
        sna = bal_menu.addAction("拖拽吸附四边")
        sna.setCheckable(True)
        sna.setChecked(self.snap_on)
        sna.triggered.connect(self.set_snap)
        fka = bal_menu.addAction("左吸附时翻面")
        fka.setCheckable(True)
        fka.setChecked(self.flip_on_left)
        fka.triggered.connect(self.set_flip_on_left)
        tca = bal_menu.addAction("每轮 Codex 对话后显示消耗")
        tca.setCheckable(True)
        tca.setChecked(self.turn_cost_on)
        tca.triggered.connect(self.set_turn_cost)
        pka = bal_menu.addAction("显示峰谷时段")
        pka.setCheckable(True)
        pka.setChecked(self.show_peak)
        pka.triggered.connect(self.set_show_peak)
        peak_menu = bal_menu.addMenu("峰谷文案")
        for style in PEAK_TEXT_STYLES:
            a = peak_menu.addAction(style)
            a.setCheckable(True)
            a.setChecked(self.peak_style == style)
            a.triggered.connect(lambda _, s=style: self.set_peak_style(s))
        snd_menu = m.addMenu("音效")
        so = snd_menu.addAction("按键音效")
        so.setCheckable(True)
        so.setChecked(self.sound_on)
        so.triggered.connect(self.set_sound)
        pick_menu = snd_menu.addMenu("音效选择")
        for name in SOUND_SETS:
            a = pick_menu.addAction(name)
            a.setCheckable(True)
            a.setChecked(self.sound_set == name)
            a.triggered.connect(lambda _, n=name: self.set_sound_set(n))
        vol_menu = snd_menu.addMenu("音量")
        vol_action = QWidgetAction(vol_menu)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(0, 100)
        slider.setValue(int(self.volume * 100))
        slider.setFixedWidth(130)
        slider.valueChanged.connect(lambda v: self.set_volume(v / 100.0))
        vol_action.setDefaultWidget(slider)
        vol_menu.addAction(vol_action)
        snd_menu.addSeparator()
        snd_menu.addAction("试听音效", self.preview_sounds)
        m.addSeparator()
        m.addAction("显示/隐藏", self.toggle_visible)
        m.addAction("回到屏幕内", self.snap_into_screen)
        pa = m.addAction("鼠标穿透（点不到它）")
        pa.setCheckable(True)
        pa.setChecked(self.cfg["passthrough"])
        pa.triggered.connect(lambda on: self.set_passthrough(on))
        pra = m.addAction("进程提醒（开应用时冒泡）")
        pra.setCheckable(True)
        pra.setChecked(self.process_alerts)
        pra.triggered.connect(self.set_process_alerts)
        aa = m.addAction("开机自启")
        aa.setCheckable(True)
        aa.setChecked(self.cfg["autostart"])
        aa.triggered.connect(lambda on: self.set_autostart(on))
        m.addSeparator()
        m.addAction("退出", self.quit_app)
        return m

    def set_balance_source(self, name):
        """切换余额来源（DeepSeek / 用户自己加的其他服务）。"""
        self.cfg["balance_source"] = name
        self.balance = None           # 换来源先清掉旧数据，免得数错
        self.save_config()
        self.refresh_balance(silent=False)

    def add_other_key_dialog(self):
        """添加别的服务的 API Key（例如 OpenRouter）。"""
        with self._ui_guard():
            name, ok = QInputDialog.getText(
                self, "添加其他 API Key",
                "服务名称（例如 OpenRouter / OpenAI / Kimi）:",
                QLineEdit.EchoMode.Normal, "", Qt.WindowType.WindowStaysOnTopHint)
        if not ok or not name.strip():
            return
        name = name.strip()
        with self._ui_guard():
            key, ok2 = QInputDialog.getText(
                self, f"{name} 的 API Key",
                f"粘贴 {name} 的 API Key（只存在本地 config.json）:",
                QLineEdit.EchoMode.Password, "", Qt.WindowType.WindowStaysOnTopHint)
        if not ok2 or not key.strip():
            return
        keys = [k for k in (self.cfg.get("other_keys") or []) if k.get("name") != name]
        keys.append({"name": name, "key": key.strip()})
        self.cfg["other_keys"] = keys
        self.cfg["balance_source"] = name
        self.save_config()
        self.say(f"记下 {name} 的 Key 了，我去看看")
        self.refresh_balance(silent=False)

    def remove_other_key_dialog(self):
        keys = list(self.cfg.get("other_keys") or [])
        if not keys:
            self.say("还没有添加别的 Key 呢")
            return
        names = [k.get("name", "?") for k in keys]
        with self._ui_guard():
            pick, ok = QInputDialog.getItem(self, "删除其他 API Key", "删掉哪个？",
                                            names, 0, False,
                                            Qt.WindowType.WindowStaysOnTopHint)
        if not ok or not pick:
            return
        self.cfg["other_keys"] = [k for k in keys if k.get("name") != pick]
        if (self.cfg.get("balance_source") or "DeepSeek") == pick:
            self.cfg["balance_source"] = "DeepSeek"
            self.balance = None
        self.save_config()
        self.say(f"已删除 {pick} 的 Key")
        self.refresh_balance(silent=True)

    def _set_key_dialog(self):
        with self._ui_guard():
            key, ok = QInputDialog.getText(
                self,
                "设置 DeepSeek Key",
                "输入你的 API Key（从 platform.deepseek.com 获取）:",
                QLineEdit.EchoMode.Normal,
                self.cfg.get("ds_api_key", ""),
                Qt.WindowType.WindowStaysOnTopHint
            )
        if ok and key.strip():
            self.cfg["ds_api_key"] = key.strip()
            self.say("Key 设置成功！我看看还剩多少钱")
            self.refresh_balance(silent=False)
        elif ok and not key.strip():
            self.say("Key 不能为空")

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self.tray.setContextMenu(self._make_menu())
        elif reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_visible()

    def _make_menu(self):
        """建右键菜单：菜单本身置顶，并且打开期间让桌宠站住不动。"""
        m = self._build_menu()
        m.setWindowFlags(m.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        m.aboutToShow.connect(lambda: setattr(self, "ui_open", True))
        m.aboutToHide.connect(lambda: setattr(self, "ui_open", False))
        return m

    def _open_menu(self, pos):
        """弹右键菜单。

        用 exec() 走 Qt 的弹出菜单模态循环：二级菜单能正常悬停展开、贴屏幕边缘时
        也会自动往反方向弹。之前用 popup + 定时 raise_() 会把子菜单顶掉，
        鼠标离开一级菜单整个菜单就消失，所以改回 exec()；菜单开着的时候
        桌宠本身也不再抢置顶（见 _keep_on_top），不会被压住。
        """
        m = self._make_menu()
        try:
            m.exec(pos)
        finally:
            self.ui_open = False

    def _ui_guard(self):
        """对话框期间用的上下文管理器：桌宠站住不动，免得盖住对话框。"""
        pet = self

        class _Guard:
            def __enter__(self):
                pet.ui_open = True

            def __exit__(self, *exc):
                pet.ui_open = False
                return False

        return _Guard()

    def contextMenuEvent(self, e):
        self._open_menu(e.globalPos())

    # ---------- 功能 ----------
    def set_mode(self, mode):
        self.mode = mode
        self.target = None
        self.cfg["mode"] = mode

    def set_balance_always(self, on):
        self.balance_always = bool(on)
        self.cfg["balance_always"] = bool(on)
        if on and self.balance is None:
            self.refresh_balance(silent=False)
        self.update()

    def set_show_peak(self, on):
        self.show_peak = bool(on)
        self.cfg["show_peak"] = bool(on)
        self.update()

    def set_peak_style(self, style):
        if style not in PEAK_TEXT_STYLES:
            return
        self.peak_style = style
        self.cfg["peak_style"] = style
        self.update()

    # ---------- 层级 / 透明度 ----------
    LAYER_LABELS = {"top": "置顶", "bottom": "置底（在壁纸之上）", "normal": "普通层"}

    def set_layer(self, layer):
        """top = 始终置顶；bottom = 沉到所有窗口下面（但仍在壁纸/桌面之上）；normal = 普通。"""
        if layer not in self.LAYER_LABELS:
            return
        self.layer = layer
        self.cfg["layer"] = layer
        self.cfg["topmost"] = (layer == "top")
        self._apply_layer()
        self.say({"top": "我回到最上面啦",
                  "bottom": "我到最下面了（壁纸上面那种）",
                  "normal": "我站在普通层，谁点谁在上面"}[layer])

    def _apply_layer(self):
        """用 Win32 精确摆放层级：HWND_TOPMOST / HWND_BOTTOM / HWND_NOTOPMOST。"""
        try:
            HWND_TOPMOST, HWND_NOTOPMOST, HWND_BOTTOM = -1, -2, 1
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
            after = {"top": HWND_TOPMOST, "bottom": HWND_BOTTOM,
                     "normal": HWND_NOTOPMOST}.get(self.layer, HWND_TOPMOST)
            ctypes.windll.user32.SetWindowPos(
                ctypes.c_void_p(int(self.winId())), ctypes.c_void_p(after),
                0, 0, 0, 0, SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    def set_opacity(self, value):
        """整体透明度 0.2 ~ 1.0（太低就看不见了，所以留个下限）。"""
        value = max(0.2, min(1.0, float(value)))
        self.opacity = value
        self.cfg["opacity"] = value
        self.setWindowOpacity(value)

    def set_process_alerts(self, on):
        self.process_alerts = bool(on)
        self.cfg["process_alerts"] = bool(on)
        if on:
            self.say("好嘞，你开什么我都盯着")

    def set_snap(self, on):
        self.snap_on = bool(on)
        self.cfg["snap_on"] = bool(on)
        if not on:
            self.snap_h = self.snap_v = None
            self.flip_x = False
        self.update()

    def set_flip_on_left(self, on):
        self.flip_on_left = bool(on)
        self.cfg["flip_on_left"] = bool(on)
        if not on:
            self.flip_x = False
        self.update()

    def set_turn_cost(self, on):
        self.turn_cost_on = bool(on)
        self.cfg["turn_cost_on"] = bool(on)

    def set_size(self, mult):
        self.cur_h = int(340 * mult)
        self.cfg["size"] = mult
        self.cross_t = 0.0
        self.prev_key = None
        self.win_mx = int(self.cur_h * 0.062) + 6
        self.win_w = max(p.width() for k, p in self.sprites.items() if k[1] == self.cur_h) + self.win_mx * 2
        self.setFixedSize(self.win_w, self.cur_h + BUBBLE_H + MARGIN * 2 + 10)
        self.snap_into_screen()

    def snap_into_screen(self):
        geo = (self.screen() or QApplication.primaryScreen()).availableGeometry()
        x = max(geo.left(), min(geo.right() - self.width(), self.x()))
        y = max(geo.top(), min(geo.bottom() - self.height(), self.y()))
        self.move(x, y)
        self._settle(geo)

    def _keep_on_top(self):
        """定期把自己顶到置顶窗口的最前面（SWP_NOACTIVATE，不抢焦点）。

        有的窗口（例如 Codex 主窗口）本身也是置顶的，两个置顶窗口重叠时就按 z 序排，
        不主动提一下的话桌宠会被盖住。
        """
        if (not self.cfg.get("topmost", True) or not self.isVisible()
                or self.ui_open):     # 菜单/对话框开着时别抢，免得盖住设置面板
            return
        try:
            self.raise_()          # 先把窗口抬到同类窗口最前面
        except Exception:
            pass
        try:
            SWP_NOSIZE, SWP_NOMOVE, SWP_NOACTIVATE = 0x0001, 0x0002, 0x0010
            ctypes.windll.user32.SetWindowPos(
                ctypes.c_void_p(int(self.winId())),
                ctypes.c_void_p(-1),          # HWND_TOPMOST（必须按指针传，直接传 -1 会被截断）
                0, 0, 0, 0,
                SWP_NOSIZE | SWP_NOMOVE | SWP_NOACTIVATE)
        except Exception:
            pass

    def _apply_passthrough(self, on):
        hwnd = int(self.winId())
        GWL_EXSTYLE, WS_EX_LAYERED, WS_EX_TRANSPARENT = -20, 0x80000, 0x20
        style = ctypes.windll.user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        style = style | WS_EX_LAYERED
        if on:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
        ctypes.windll.user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, style)

    def set_passthrough(self, on):
        self.cfg["passthrough"] = bool(on)
        self._apply_passthrough(bool(on))
        if on:
            self.say("我隐身了！右键托盘图标解除～")

    def set_topmost(self, on):
        self.cfg["topmost"] = bool(on)
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, bool(on))
        self.show()

    def set_autostart(self, on):
        self.cfg["autostart"] = bool(on)
        lnk = os.path.join(os.environ["APPDATA"], "Microsoft", "Windows",
                           "Start Menu", "Programs", "Startup", "大肥鱼桌宠.lnk")
        try:
            if on:
                ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{}');"
                      "$s.TargetPath='{}';$s.Arguments='\"{}\"';$s.WorkingDirectory='{}';$s.Save()"
                      .format(lnk, PYTHONW,
                              "" if getattr(sys, "frozen", False) else os.path.join(APP_DIR, "桌宠.py"),
                              APP_DIR))
                subprocess.run(["powershell", "-NoProfile", "-Command", ps],
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0), check=True)
                self.say("已开机自启，明天见～")
            else:
                if os.path.exists(lnk):
                    os.remove(lnk)
                self.say("已取消开机自启")
        except Exception as ex:
            QMessageBox.warning(self, "开机自启", f"设置失败：{ex}")

    def toggle_visible(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()
            self.raise_()

    def quit_app(self):
        self.cfg["x"], self.cfg["y"] = self.x(), self.y()
        self.save_config()
        self.tray.hide()
        QApplication.quit()


SINGLE_INSTANCE_KEY = "dafeiyu-pet-whale-single-instance"


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    # 单实例：已经在跑了就把那一只叫出来，不再开第二只（快捷方式 / 源码双击都一样）
    server = None
    try:
        from PySide6.QtNetwork import QLocalServer, QLocalSocket
        probe = QLocalSocket()
        probe.connectToServer(SINGLE_INSTANCE_KEY)
        if probe.waitForConnected(300):
            probe.write(b"show")
            probe.flush()
            probe.waitForBytesWritten(300)
            return 0
        QLocalServer.removeServer(SINGLE_INSTANCE_KEY)
        server = QLocalServer()
        server.listen(SINGLE_INSTANCE_KEY)
    except Exception:
        server = None

    w = PetWindow()

    if server is not None:
        def on_new_connection():
            sock = server.nextPendingConnection()
            if sock is not None:
                sock.disconnectFromServer()
            w.show()
            w.raise_()
            w.say("我在这儿呢，有我这只就够啦")
        server.newConnection.connect(on_new_connection)

    sys.exit(app.exec())


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        try:
            app = QApplication.instance() or QApplication(sys.argv)
            QMessageBox.critical(None, "大肥鱼桌宠出错", str(ex))
        except Exception:
            pass
        raise
