# -*- coding: utf-8 -*-
"""桌宠控制台 —— v1.1.0 起的新设置界面（左侧分类 + 右侧内容）。

为什么要单独一个文件：这是全新的界面子系统（主题 / 图标 / 控件 / 十几个页面），
塞进 6800 行的 `桌宠.py` 里以后没地方改。PyInstaller 会跟着 `import ui_console`
自动收进去，打包只多一步：把 `assets/icons` 加进 `桌宠.spec` 的 datas。

两条硬规矩（2026-09-14 定的）：
  1. 图标一律单色，颜色走 currentColor，随亮/暗主题换色；
  2. 主题分「跟随系统 / 亮色 / 暗色」三档，默认跟随系统；
     Qt 说不清系统是亮是暗时退回读注册表 AppsUseLightTheme。

外面的 桌宠.py 只做三件事：菜单里开这个窗口、把常量表（ctx）递进来、退出时关掉。
界面逻辑全在本文件里。
"""

import ctypes
import os
import time
from string import Template

from PySide6.QtCore import (QAbstractNativeEventFilter, QEasingCurve, QEvent,
                            QParallelAnimationGroup, QPoint, QPropertyAnimation,
                            QRect, QRectF, QSize, Qt, QTimer, QVariantAnimation)
from PySide6.QtGui import QColor, QCursor, QFont, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import (QAbstractButton, QApplication, QButtonGroup,
                               QComboBox, QFrame, QHBoxLayout, QLabel,
                               QPushButton, QScrollArea, QSizePolicy, QSlider,
                               QStackedWidget, QVBoxLayout, QWidget)

try:
    from PySide6.QtSvg import QSvgRenderer
    SVG_OK = True
except Exception:          # 缺 QtSvg 也不该让桌宠起不来：图标位置留空就是
    SVG_OK = False


# 界面自己的版本号。发版时跟着一起改（关于页和侧边栏底部都读它）。
APP_VERSION = "1.1.0"

# 最小化动画时长（毫秒）：照着 Windows 那套"往任务栏收"的感觉来
MINIMIZE_ANIM_MS = 190
# 动画节拍：**自己去插值**，一拍 8ms（≈120fps）。
# Qt 自带的动画走的是全局统一计时器（默认 16ms ≈ 60fps），时长相同时帧数只有一半，
# 所以同一段 190ms 我们按 8ms 走 —— 时间不变、帧数翻倍。
ANIM_TICK_MS = 8

GITHUB_URL = "https://github.com/RYANFFY/deepseek-dafeiyu-pet"


# --------------------------------------------------------------------------- #
# 主题
# --------------------------------------------------------------------------- #
# 一套亮、一套暗。键名就是"哪儿用"，别在页面里写死颜色，全从这儿取。
THEMES = {
    "light": {
        "bg": "#f5f6fa",
        "sidebar": "#eceef5",
        "surface": "#ffffff",
        "surface_alt": "#e9ebf3",
        "border": "#e0e3ec",
        "text": "#1d2030",
        "nav_text": "#4d5366",
        "text_dim": "#7b8093",
        "text_faint": "#a2a7b8",
        "accent": "#3b7bf6",
        "accent_hover": "#2f6ae0",
        "accent_soft": "#e3ecfe",
        "accent_text": "#ffffff",
        "seg_on": "#ffffff",
        "switch_off": "#d3d7e3",
        "ok": "#2e9e5b",
        "warn": "#c9770f",
        "danger": "#e04a4a",
        "scroll": "#ccd0dd",
        "shadow": QColor(0, 0, 0, 45),
    },
    "dark": {
        "bg": "#171a24",
        "sidebar": "#12141d",
        "surface": "#1f2331",
        "surface_alt": "#282d3d",
        "border": "#313748",
        "text": "#e9ebf4",
        "nav_text": "#a8aec2",
        "text_dim": "#979db2",
        "text_faint": "#6b7186",
        "accent": "#5b9dff",
        "accent_hover": "#78b0ff",
        "accent_soft": "#20304c",
        "accent_text": "#0d1220",
        "seg_on": "#3b4460",
        "switch_off": "#3a4157",
        "ok": "#43c07a",
        "warn": "#e0a04a",
        "danger": "#ff6b6b",
        "scroll": "#3d4459",
        "shadow": QColor(0, 0, 0, 110),
    },
}

THEME_MODES = [("system", "跟随系统"), ("light", "亮色"), ("dark", "暗色")]

_mode = "system"
_current = dict(THEMES["light"])


def system_scheme():
    """系统现在是亮还是暗。Qt 说不出来（老旧系统 / 离屏）就退回读注册表。"""
    try:
        from PySide6.QtGui import QGuiApplication
        scheme = QGuiApplication.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return "dark"
        if scheme == Qt.ColorScheme.Light:
            return "light"
    except Exception:
        pass
    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize")
        value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
        return "light" if int(value) else "dark"
    except Exception:
        return "light"


def get_mode():
    return _mode


def set_mode(mode):
    global _mode
    _mode = mode if mode in ("system", "light", "dark") else "system"
    return refresh_tokens()


def refresh_tokens():
    """按当前模式重算调色板，返回实际生效的亮/暗。"""
    global _current
    effective = system_scheme() if _mode == "system" else _mode
    _current = dict(THEMES[effective])
    return effective


def tokens():
    return _current


# --------------------------------------------------------------------------- #
# 图标（单色 SVG，用 currentColor 换色；随主题重画）
# --------------------------------------------------------------------------- #
_ICON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "icons")
_ICON_CACHE = {}


def set_asset_dir(asset_dir):
    """由 桌宠.py 把 ASSET_DIR 递进来，省得自己猜打包后的路径。"""
    global _ICON_DIR
    if asset_dir:
        _ICON_DIR = os.path.join(asset_dir, "icons")


def icon_path(name):
    return os.path.join(_ICON_DIR, name + ".svg")


def icon_pixmap(name, color, size=18):
    """把某个图标渲染成指定颜色的位图（2 倍分辨率，高分屏不糊）。"""
    key = (name, color, size)
    hit = _ICON_CACHE.get(key)
    if hit is not None:
        return hit
    dpr = 2.0
    pix = QPixmap(int(size * dpr), int(size * dpr))
    pix.fill(Qt.GlobalColor.transparent)
    if SVG_OK:
        try:
            with open(icon_path(name), "r", encoding="utf-8") as fp:
                source = fp.read().replace("currentColor", color)
            renderer = QSvgRenderer(source.encode("utf-8"))
            painter = QPainter(pix)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
            renderer.render(painter)
            painter.end()
        except Exception:
            pass
    pix.setDevicePixelRatio(dpr)
    _ICON_CACHE[key] = pix
    return pix


def icon(name, color, size=18):
    return QIcon(icon_pixmap(name, color, size))


def clear_icon_cache():
    """换主题时清一遍（同一张图要按新颜色重画）。"""
    _ICON_CACHE.clear()


def bundle_icon(bundle_dir):
    """窗口 / 任务栏用的图标。

    原来全项目一个 `setWindowIcon` 都没有 → 任务栏上是一只**空白方块**（Windows
    找不到图标时的占位图）。这里优先用打包用的 `icon.ico`（16~256 各尺寸都齐），
    退回 `sprites/icon.png`。
    """
    for rel in ("icon.ico", os.path.join("sprites", "icon.png")):
        path = os.path.join(bundle_dir or "", rel)
        try:
            if os.path.exists(path):
                ico = QIcon(path)
                if not ico.isNull():
                    return ico
        except Exception:
            pass
    return QIcon()


def style_dialog(dlg, bundle_dir=None):
    """把设置窗口那套配色套到老对话框上（形象库 / 上传形象 / 扫描应用 / 各种小窗口）。

    这些窗口原来是 Qt 默认灰样式，跟新界面放一起像两个软件。套上同一份调色板，
    字体、按钮、下拉、列表、输入框就都统一了。
    """
    refresh_tokens()
    clear_icon_cache()
    dlg.setStyleSheet(build_qss())
    dlg.setFont(QFont("Microsoft YaHei UI", 9))
    ico = bundle_icon(bundle_dir)
    if not ico.isNull():
        dlg.setWindowIcon(ico)


# --------------------------------------------------------------------------- #
# 样式表
# --------------------------------------------------------------------------- #
_QSS = Template("""
QWidget#shellRoot { font-family: "Microsoft YaHei UI", "Microsoft YaHei", "Segoe UI"; }
QFrame#shell { background: $bg; border: 1px solid $border; border-radius: 14px; }
QFrame#sidebar { background: $sidebar; border: none;
                 border-top-left-radius: 13px; border-bottom-left-radius: 13px; }
QFrame#header, QFrame#main { background: transparent; border: none; }
QLabel { color: $text; font-size: 13px; background: transparent; }
QLabel#brand { font-size: 14px; font-weight: 700; }
QLabel#pageTitle { font-size: 19px; font-weight: 700; }
QLabel#pageDesc { color: $text_dim; font-size: 12px; }
QLabel#cardTitle { font-size: 13px; font-weight: 700; }
QLabel#cardDesc { color: $text_faint; font-size: 11px; }
QLabel#rowTitle { font-size: 13px; }
QLabel#rowDesc { color: $text_dim; font-size: 11px; }
QLabel#big { font-size: 30px; font-weight: 700; }
QLabel#muted { color: $text_dim; font-size: 12px; }
QLabel#faint { color: $text_faint; font-size: 11px; }
QLabel#ok { color: $ok; font-size: 12px; }
QLabel#warn { color: $warn; font-size: 12px; }
QLabel#danger { color: $danger; font-size: 12px; }
QFrame#card { background: $surface; border: 1px solid $border; border-radius: 12px; }
QFrame#divider { background: $border; border: none; max-height: 1px; }
QFrame#segBox { background: $surface_alt; border: none; border-radius: 9px; }
QPushButton#segBtn { background: transparent; border: none; border-radius: 7px;
                     padding: 5px 12px; color: $text_dim; font-size: 12px; }
QPushButton#segBtn:hover { color: $text; }
QPushButton#segBtn:checked { background: $seg_on; color: $text; font-weight: 700; }
QPushButton { background: $surface; border: 1px solid $border; border-radius: 8px;
              padding: 6px 14px; color: $text; font-size: 12px; }
/* hover 只换底色，不换细边框的颜色：这台机器 125% 缩放时，
   1px 边框在 hover 重绘那一下容易画丢顶边（看着像被什么挡了一截）。 */
QPushButton:hover { background: $surface_alt; border-color: $border; }
QPushButton:pressed { background: $surface_alt; }
QPushButton:disabled { color: $text_faint; border-color: $border; }
QPushButton#primary { background: $accent; border: 1px solid $accent;
                      color: $accent_text; font-weight: 700; }
QPushButton#primary:hover { background: $accent_hover; border-color: $accent_hover;
                            color: $accent_text; }
QPushButton#danger { color: $danger; }
QPushButton#danger:hover { background: $surface_alt; border-color: $danger;
                           color: $danger; }
QPushButton#winBtn { background: transparent; border: none; padding: 5px; border-radius: 6px; }
QPushButton#winBtn:hover { background: $surface_alt; }
QComboBox { background: $surface_alt; border: 1px solid $border; border-radius: 8px;
            padding: 5px 8px; color: $text; font-size: 12px; min-width: 132px; }
QComboBox:hover { background: $surface; border-color: $accent; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox::down-arrow { image: url($chevron); width: 11px; height: 11px; }
QComboBox QAbstractItemView { background: $surface; color: $text;
            border: 1px solid $border; outline: none; padding: 4px;
            selection-background-color: $accent_soft; selection-color: $text; }
QLineEdit { background: $surface_alt; border: 1px solid $border; border-radius: 8px;
            padding: 6px 10px; color: $text; font-size: 12px; }
QLineEdit:focus { border-color: $accent; background: $surface; }
QSlider::groove:horizontal { height: 4px; background: $surface_alt; border-radius: 2px; }
QSlider::sub-page:horizontal { background: $accent; border-radius: 2px; }
QSlider::handle:horizontal { width: 14px; margin: -6px 0; border-radius: 7px;
                             background: #ffffff; border: 1px solid $border; }
QSlider::handle:horizontal:hover { border-color: $accent; }
QDialog { background: $bg; }
QListWidget { background: $surface; border: 1px solid $border; border-radius: 10px;
              color: $text; font-size: 12px; outline: none; padding: 4px; }
QListWidget::item { padding: 6px 8px; border-radius: 6px; }
QListWidget::item:hover { background: $surface_alt; }
QListWidget::item:selected { background: $accent_soft; color: $text; }
QPlainTextEdit, QTextEdit { background: $surface_alt; border: 1px solid $border;
              border-radius: 8px; color: $text; font-size: 12px; padding: 6px; }
QPlainTextEdit:focus, QTextEdit:focus { border-color: $accent; }
QCheckBox, QRadioButton { color: $text; font-size: 12px; }
QLabel#thumb { border: 1px dashed $border; border-radius: 8px; color: $text_faint; }
QLabel#thumbOn { border: 1px solid $border; border-radius: 8px; }
QLabel#dim { color: $text_dim; }
QLabel#warnText { color: $warn; }
QLabel#okText { color: $ok; }
QLabel#preview { border: 1px solid $border; border-radius: 10px; color: $text_faint;
                 background: $surface; }
/* 滚动区域用**实色**底：这样视口可以标成"不透明"，滚动时不用连带重画父窗口
   （无边框 + 半透明窗口上，每滚一帧都把整窗重画一遍就会掉帧）。 */
QScrollArea { background: $bg; border: none; }
QWidget#pageInner { background: $bg; }
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle:vertical { background: $scroll; border-radius: 5px; min-height: 32px; }
QScrollBar::handle:vertical:hover { background: $accent; }
QScrollBar::handle:horizontal { background: $scroll; border-radius: 5px; min-width: 32px; }
QScrollBar::handle:horizontal:hover { background: $accent; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; width: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
""")


def build_qss():
    data = dict(tokens())
    data["chevron"] = icon_path("ui.chevron-down").replace("\\", "/")
    return _QSS.substitute(data)


# --------------------------------------------------------------------------- #
# 小控件
# --------------------------------------------------------------------------- #
class Switch(QAbstractButton):
    """小开关（轨道 + 圆钮）。颜色跟着主题走，所以 paintEvent 里现取。"""

    def __init__(self, checked=False, on_change=None, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setChecked(bool(checked))
        # 高度取 24：125% 缩放时正好 30 物理像素（26 会落在半像素上，
        # 一列控件累积下来，细边框那几条线就会忽隐忽现）
        self.setFixedSize(44, 24)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        if on_change is not None:
            self.toggled.connect(on_change)

    def sizeHint(self):
        return QSize(44, 24)

    def paintEvent(self, _ev):
        t = tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        track = QRectF(1.0, 3.0, self.width() - 2.0, self.height() - 6.0)
        radius = track.height() / 2.0
        if not self.isEnabled():
            color = t["surface_alt"]
        elif self.isChecked():
            color = t["accent"]
        else:
            color = t["switch_off"]
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(color))
        painter.drawRoundedRect(track, radius, radius)
        knob = track.height() - 5.0
        x = track.right() - knob - 2.5 if self.isChecked() else track.left() + 2.5
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(QRectF(x, track.top() + 2.5, knob, knob))
        painter.end()


class Segmented(QWidget):
    """一排互斥按钮（"三选一"那种），比下拉框点得少。"""

    def __init__(self, options, current=None, on_change=None, parent=None):
        super().__init__(parent)
        self._on_change = on_change
        self._buttons = {}
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        box = QFrame()
        box.setObjectName("segBox")
        line = QHBoxLayout(box)
        line.setContentsMargins(3, 3, 3, 3)
        line.setSpacing(2)
        self._group = QButtonGroup(self)
        self._group.setExclusive(True)
        for value, label in options:
            btn = QPushButton(label)
            btn.setObjectName("segBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setChecked(value == current)
            btn.clicked.connect(lambda _=False, v=value: self._pick(v))
            line.addWidget(btn)
            self._group.addButton(btn)
            self._buttons[value] = btn
        outer.addWidget(box)
        outer.addStretch(1)

    def _pick(self, value):
        if self._on_change is not None:
            self._on_change(value)

    def set_value(self, value):
        """选中某一项；传 None（或找不到）就把整排取消选中。"""
        btn = self._buttons.get(value)
        if btn is None:
            self._group.setExclusive(False)
            for one in self._buttons.values():
                one.setChecked(False)
            self._group.setExclusive(True)
            return
        if not btn.isChecked():
            btn.setChecked(True)


class NavItem(QAbstractButton):
    """左侧一条分类：图标 + 文字，选中时铺一层主题色底片。"""

    def __init__(self, key, text, icon_name, parent=None):
        super().__init__(parent)
        self.key = key
        self.icon_name = icon_name
        self.setText(text)
        self.setCheckable(True)
        self.setFixedHeight(36)          # 36 = 45 物理像素（125% 下是整数）
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._hover = False

    def enterEvent(self, _ev):
        self._hover = True
        self.update()

    def leaveEvent(self, _ev):
        self._hover = False
        self.update()

    def paintEvent(self, _ev):
        t = tokens()
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        if self.isChecked():
            bg, fg = t["accent_soft"], t["accent"]
        elif self._hover:
            bg, fg = t["surface_alt"], t["text"]
        else:
            bg, fg = None, t["nav_text"]
        if bg is not None:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(bg))
            painter.drawRoundedRect(
                QRectF(0.0, 0.5, float(self.width()), self.height() - 1.0), 9, 9)
        painter.drawPixmap(11, (self.height() - 18) // 2,
                           icon_pixmap(self.icon_name, fg, 18))
        font = QFont(self.font())
        font.setPixelSize(13)
        font.setBold(self.isChecked())
        painter.setFont(font)
        painter.setPen(QColor(fg))
        painter.drawText(
            QRectF(39, 0, self.width() - 48, float(self.height())),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            self.text())
        painter.end()


class _NativeMsg(ctypes.Structure):
    """原生消息（只用到前面几个字段）。"""
    _fields_ = [("hWnd", ctypes.c_void_p), ("message", ctypes.c_uint),
                ("wParam", ctypes.c_void_p), ("lParam", ctypes.c_void_p)]


class _MinimizeGuard(QAbstractNativeEventFilter):
    """把"从系统那边来的最小化"也接过来，改走我们那套缩放动画。

    来源包括：点任务栏图标、系统菜单里的「最小化」、Alt+空格+M。

    为什么必须拦：我们的窗口是无边框 + 半透明（分层窗口），
    Windows **不会**给它跑最小化动画（实测：`ShowWindow(SW_MINIMIZE)` 之后
    窗口矩形一采样就跳到 -32000，压根没有过渡帧）。
    所以这里在原生消息层把 `SC_MINIMIZE` 吃掉，自己放动画 ——
    这样"点任务栏图标"和"点右上角那颗按钮"看到的是同一套动画。
    """

    WM_SYSCOMMAND = 0x0112
    SC_MINIMIZE = 0xF020
    SC_RESTORE = 0xF120

    def __init__(self, window):
        super().__init__()
        self._win = window

    def nativeEventFilter(self, _event_type, message):
        try:
            msg = ctypes.cast(int(message), ctypes.POINTER(_NativeMsg)).contents
        except Exception:
            return False, 0
        if msg.message != self.WM_SYSCOMMAND:
            return False, 0
        command = int(msg.wParam) & 0xFFF0
        if command not in (self.SC_MINIMIZE, self.SC_RESTORE):
            return False, 0
        try:
            if int(msg.hWnd) != int(self._win.winId()):
                return False, 0            # 不是我们这个窗口的最小化，别管
        except Exception:
            return False, 0
        # 不能在过滤器里直接跑动画（还在消息处理里），下一拍再说。
        # SC_MINIMIZE = 点任务栏图标/系统菜单要最小化；SC_RESTORE = 最小化着再点一次要还原
        if command == self.SC_RESTORE:
            QTimer.singleShot(0, self._win.restore_with_anim)
        else:
            QTimer.singleShot(0, self._win.minimize_with_anim)
        return True, 0                     # 吃掉：不让系统自己 minimize（否则会先闪一下）


class DragBar(QFrame):
    """标题栏：空白处按住能拖窗口（子控件自己吃掉点击，互不打架）。"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_from = None

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            window = self.window()
            self._drag_from = (ev.globalPosition().toPoint()
                               - window.frameGeometry().topLeft())
            ev.accept()
        else:
            super().mousePressEvent(ev)

    def mouseMoveEvent(self, ev):
        if self._drag_from is not None and ev.buttons() & Qt.MouseButton.LeftButton:
            self.window().move(ev.globalPosition().toPoint() - self._drag_from)
            ev.accept()
        else:
            super().mouseMoveEvent(ev)

    def mouseReleaseEvent(self, ev):
        self._drag_from = None
        super().mouseReleaseEvent(ev)


class Page(QScrollArea):
    """一页内容。卡片 / 行 / 分隔线都从这儿长出来，风格自然统一。"""

    def __init__(self, title, desc=""):
        super().__init__()
        self.title = title
        self.desc = desc
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        # 视口自己把底色铺满（QSS 里给了实色底），滚动时就不用连父窗口一起重画
        self.viewport().setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        inner = QWidget()
        inner.setObjectName("pageInner")
        self.body = QVBoxLayout(inner)
        self.body.setContentsMargins(22, 2, 22, 22)
        self.body.setSpacing(14)
        self.body.addStretch(1)
        self.setWidget(inner)
        self._card_icons = []

    # ---- 积木 ----
    def card(self, title, desc="", icon_name=None):
        """加一张卡片，返回它的内容布局（往里面放行）。"""
        frame = QFrame()
        frame.setObjectName("card")
        box = QVBoxLayout(frame)
        box.setContentsMargins(16, 13, 16, 14)
        box.setSpacing(11)
        head = QHBoxLayout()
        head.setSpacing(8)
        if icon_name:
            mark = QLabel()
            mark.setFixedSize(17, 17)
            mark.setPixmap(icon_pixmap(icon_name, tokens()["accent"], 17))
            self._card_icons.append((mark, icon_name))
            head.addWidget(mark)
        label = QLabel(title)
        label.setObjectName("cardTitle")
        head.addWidget(label)
        head.addStretch(1)
        if desc:
            hint = QLabel(desc)
            hint.setObjectName("cardDesc")
            head.addWidget(hint)
        box.addLayout(head)
        self.body.insertWidget(self.body.count() - 1, frame)
        return box

    def row(self, layout, title, desc="", control=None):
        wrap = QWidget()
        line = QHBoxLayout(wrap)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(12)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        name = QLabel(title)
        name.setObjectName("rowTitle")
        col.addWidget(name)
        if desc:
            sub = QLabel(desc)
            sub.setObjectName("rowDesc")
            sub.setWordWrap(True)
            col.addWidget(sub)
        line.addLayout(col, 1)
        if control is not None:
            line.addWidget(control, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(wrap)
        return wrap

    def buttons(self, layout, items, align_right=True):
        """一行按钮：items = [(文字, 回调, 样式名 or None), …]。"""
        wrap = QWidget()
        line = QHBoxLayout(wrap)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(8)
        if align_right:
            line.addStretch(1)
        for text, slot, style in items:
            btn = QPushButton(text)
            # 固定高度 32：125% 缩放下 = 整 40 物理像素（30 会落在半像素上，
            # 细边框和圆角那一下容易画糊）
            btn.setFixedHeight(32)
            if style:
                btn.setObjectName(style)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            if slot is not None:
                btn.clicked.connect(lambda _=False, f=slot: f())
            line.addWidget(btn)
        if not align_right:
            line.addStretch(1)
        layout.addWidget(wrap)
        return wrap

    def hint(self, layout, text, style="faint"):
        label = QLabel(text)
        label.setObjectName(style)
        label.setWordWrap(True)
        layout.addWidget(label)
        return label

    def divider(self, layout):
        line = QFrame()
        line.setObjectName("divider")
        line.setFixedHeight(1)
        layout.addWidget(line)
        return line

    def slider(self, layout, title, desc, low, high, value, unit, on_change):
        """一行带滑块的设置：拖动时右边数字跟着变，边拖边生效。"""
        box = QWidget()
        line = QHBoxLayout(box)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(12)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        name = QLabel(title)
        name.setObjectName("rowTitle")
        col.addWidget(name)
        if desc:
            sub = QLabel(desc)
            sub.setObjectName("rowDesc")
            col.addWidget(sub)
        line.addLayout(col, 1)
        show = QLabel(f"{value}{unit}")
        show.setObjectName("muted")
        show.setFixedWidth(46)
        show.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bar = QSlider(Qt.Orientation.Horizontal)
        bar.setRange(low, high)
        bar.setValue(value)
        bar.setFixedWidth(190)
        bar.setCursor(Qt.CursorShape.PointingHandCursor)
        bar.value_label = show          # 外面要改数字（比如点档位）时用得上

        def moved(v):
            show.setText(f"{v}{unit}")
            on_change(v)

        bar.valueChanged.connect(moved)
        line.addWidget(bar, 0, Qt.AlignmentFlag.AlignVCenter)
        line.addWidget(show, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(box)
        return bar

    def combo(self, layout, title, desc, options, current, on_change):
        """一行配一个下拉框：options = [(值, 显示文字), …]。"""
        box = QComboBox()
        for value, label in options:
            box.addItem(label, value)
        for index in range(box.count()):
            if box.itemData(index) == current:
                box.setCurrentIndex(index)
                break
        box.setCursor(Qt.CursorShape.PointingHandCursor)
        box.currentIndexChanged.connect(lambda _i: on_change(box.currentData()))
        self.row(layout, title, desc, box)
        return box

    def repaint_cards(self):
        """换主题后重画卡片标题上的小图标。"""
        for label, name in self._card_icons:
            label.setPixmap(icon_pixmap(name, tokens()["accent"], 17))


# --------------------------------------------------------------------------- #
# 控制台窗口
# --------------------------------------------------------------------------- #
class ConsoleWindow(QWidget):
    """设置窗口本体。pet 是桌宠（PetWindow），ctx 是 桌宠.py 递进来的常量/函数表。

    分类只放**设置**。「看一眼余额 / 看一看天气 / 在放什么」这类是桌宠自己的活儿，
    菜单和桌宠本体上都有，不往设置里塞（v1.1.0 第一版塞过，太重复，撤了）。
    """

    PAGES = [
        ("balance", "余额和用量", "Key、来源、今日已用怎么算",
         "nav.balance", "_page_balance"),
        ("appearance", "形象和外观", "换成谁、多大、多透明、在哪一层",
         "nav.appearance", "_page_appearance"),
        ("behavior", "动作和互动", "怎么走、双击做什么、怎么防误触",
         "nav.behavior", "_page_behavior"),
        ("weather", "天气和城市", "看哪个城市的天气", "nav.weather", "_page_weather"),
        ("music", "音乐和歌词", "放歌时跟着唱", "nav.music", "_page_music"),
        ("lines", "文案和语录", "闲着时说什么、高峰时段怎么显示",
         "nav.lines", "_page_lines"),
        ("sound", "音效", "按键音效、音量、自己加的音频", "nav.sound", "_page_sound"),
        ("integration", "应用联动", "打开某些应用时它冒泡说话",
         "nav.integration", "_page_integration"),
        ("performance", "性能和工具", "流畅度、回收内存",
         "nav.performance", "_page_performance"),
        ("general", "通用", "显示、主题、开机自启、排查",
         "nav.general", "_page_general"),
        ("about", "关于", "版本与反馈", "nav.about", "_page_about"),
    ]

    def __init__(self, pet, ctx):
        super().__init__(None)
        self.pet = pet
        self.ctx = ctx or {}
        self._pages = {}
        self._nav_items = {}
        self._shadow_pm = None            # 阴影贴图缓存（见 _shadow_pixmap）
        self._shadow_key = None
        self._min_anim = None             # 最小化动画（跑着的时候不接第二次）
        self._min_pm = None               # 动画期间铺的那张"整窗截图"
        self._min_self = False            # 这一次最小化是不是我们自己发起的
        self._anim_target = None          # 正在往哪边走："min" / "restore"
        self._restoring = False
        self._restore_geo = None          # 正常大小该在哪儿
        self._min_min_size = None
        self._anim_fade = 1.0             # 动画期间那张截图的绘制不透明度（0~1）
        self._anim = None                 # 自己的动画拍子（见 _anim_tick）
        self._tick_timer = None
        # 主题要先定下来：页面里那个"主题三选一"建的时候就要知道现在选的是哪档
        self._mode = pet.cfg.get("ui_theme", "system")
        set_mode(self._mode)

        self.setWindowTitle("大肥鱼桌宠 · 设置")
        self.setWindowFlags(Qt.WindowType.Window
                            | Qt.WindowType.FramelessWindowHint
                            # 一定要带这个：Windows 只有认到 WS_MINIMIZEBOX 才会
                            # 让"点任务栏图标 = 最小化 / 再点唤出"生效
                            | Qt.WindowType.WindowMinimizeButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(820, 560)
        self.resize(920, 640)
        self.setFont(QFont("Microsoft YaHei UI", 9))
        ico = bundle_icon(self.ctx.get("BUNDLE_DIR"))
        if not ico.isNull():
            self.setWindowIcon(ico)       # 不然任务栏上是一只空白方块

        # 外面留 20px 给阴影，里面才是"真正的窗口"
        outer = QVBoxLayout(self)
        outer.setContentsMargins(20, 20, 20, 20)
        self.shell = QFrame()
        self.shell.setObjectName("shell")
        outer.addWidget(self.shell)

        body = QHBoxLayout(self.shell)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(self._build_sidebar())
        body.addWidget(self._build_main(), 1)

        self.apply_theme()
        self.switch_page("home")

        # 系统切亮暗时，只有"跟随系统"这一档要跟着变
        try:
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.styleHints().colorSchemeChanged.connect(
                self._on_system_scheme)
        except Exception:
            pass

        # 拦"点任务栏图标 / 系统菜单"那条最小化，改走我们自己的动画
        try:
            self._min_guard = _MinimizeGuard(self)
            inst = QApplication.instance()
            if inst is not None:
                inst.installNativeEventFilter(self._min_guard)
        except Exception:
            self._min_guard = None

        # 首页那几张卡（余额 / 天气 / 在放什么）要活着
        self._live = QTimer(self)
        self._live.setInterval(2000)
        self._live.timeout.connect(self._refresh_balance_card)
        self._live.start()

    # ---------------- 骨架 ----------------
    def _build_sidebar(self):
        side = QFrame()
        side.setObjectName("sidebar")
        side.setFixedWidth(210)
        box = QVBoxLayout(side)
        box.setContentsMargins(12, 16, 12, 14)
        box.setSpacing(4)

        brand = QHBoxLayout()
        brand.setContentsMargins(6, 0, 0, 10)
        brand.setSpacing(8)
        logo = QLabel()
        logo.setFixedSize(26, 26)
        logo.setPixmap(self._logo_pixmap(26))
        brand.addWidget(logo)
        title = QLabel("大肥鱼桌宠")
        title.setObjectName("brand")
        brand.addWidget(title)
        brand.addStretch(1)
        box.addLayout(brand)

        for key, title, _desc, icon_name, _builder in self.PAGES:
            item = NavItem(key, title, icon_name)
            item.clicked.connect(lambda _=False, k=key: self.switch_page(k))
            self._nav_items[key] = item
            box.addWidget(item)

        box.addStretch(1)
        foot = QLabel(f"v{APP_VERSION}")
        foot.setObjectName("faint")
        foot.setContentsMargins(8, 0, 0, 0)
        box.addWidget(foot)
        return side

    def _build_main(self):
        main = QFrame()
        main.setObjectName("main")
        box = QVBoxLayout(main)
        box.setContentsMargins(0, 0, 0, 0)
        box.setSpacing(0)

        header = DragBar()
        header.setObjectName("header")
        header.setFixedHeight(62)
        head = QHBoxLayout(header)
        head.setContentsMargins(22, 14, 14, 8)
        head.setSpacing(10)
        col = QVBoxLayout()
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(1)
        self.title_label = QLabel("")
        self.title_label.setObjectName("pageTitle")
        col.addWidget(self.title_label)
        self.desc_label = QLabel("")
        self.desc_label.setObjectName("pageDesc")
        col.addWidget(self.desc_label)
        head.addLayout(col)
        head.addStretch(1)
        for tip, icon_name in (("最小化", "ui.minimize"), ("关闭", "ui.close")):
            btn = QPushButton()
            btn.setObjectName("winBtn")
            btn.setFixedSize(30, 30)
            btn.setIconSize(QSize(16, 16))
            btn.setIcon(icon(icon_name, tokens()["text_dim"], 16))
            btn.setToolTip(tip)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            # 最小化 = 真最小化（任务栏图标还在，点一下能还原）；关闭 = 收起来
            if tip == "最小化":
                btn.clicked.connect(self.minimize_with_anim)
            else:
                btn.clicked.connect(self.hide)
            head.addWidget(btn)
        box.addWidget(header)

        self.stack = QStackedWidget()
        box.addWidget(self.stack, 1)
        for key, title, desc, _icon, builder in self.PAGES:
            page = Page(title, desc)
            self._pages[key] = page
            self.stack.addWidget(page)
            getattr(self, builder)(page)
        return main

    def _logo_pixmap(self, size):
        """侧边栏那张小鲸鱼：直接用桌宠自己的图标，不另画一份。"""
        sprite_dir = self.ctx.get("SPRITE_DIR") or ""
        pix = QPixmap(os.path.join(sprite_dir, "icon.png"))
        if pix.isNull():
            return QPixmap(size, size)
        return pix.scaled(size, size, Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)

    # ---------------- 主题 ----------------
    def apply_theme(self):
        effective = refresh_tokens()
        clear_icon_cache()
        self.setStyleSheet(build_qss())
        self._repaint_icons()
        for page in self._pages.values():
            page.repaint_cards()
        for item in self._nav_items.values():
            item.update()
        self.update()
        return effective

    def _repaint_icons(self):
        """窗口按钮这些带 QIcon 的，换主题后要重画一份。"""
        for btn in self.findChildren(QPushButton):
            if btn.objectName() != "winBtn":
                continue
            name = "ui.close" if btn.toolTip() == "关闭" else "ui.minimize"
            btn.setIcon(icon(name, tokens()["text_dim"], 16))

    def _on_system_scheme(self, _scheme=None):
        if self._mode == "system":
            self.apply_theme()

    def set_theme(self, mode):
        self._mode = mode
        # 关键：全局调色板也要跟着切 —— Switch / NavItem 这些是在 paintEvent 里
        # 现取颜色的，只改样式表它们还按旧色画。
        set_mode(mode)
        self.pet.cfg["ui_theme"] = mode
        try:
            self.pet.save_config()
        except Exception:
            pass
        self.apply_theme()
        self.pet.update()

    # ---------------- 切页 ----------------
    def switch_page(self, key):
        page = self._pages.get(key)
        if page is None:
            return
        self.stack.setCurrentWidget(page)
        self.title_label.setText(page.title)
        self.desc_label.setText(page.desc)
        for name, item in self._nav_items.items():
            item.setChecked(name == key)
        if key == "balance":
            self._refresh_balance_card()
        elif key == "appearance":
            self._sync_size_controls()

    # ---------------- 余额那张卡（开着窗口就自己刷）----------------
    def _refresh_balance_card(self):
        if (not self.isVisible()
                or self.stack.currentWidget() is not self._pages["balance"]):
            return
        pet = self.pet
        balance = getattr(pet, "balance", None)
        symbol = self.ctx.get("currency_symbol", lambda _c: "¥")
        if not balance:
            self.bal_amount.setText("—")
            self.bal_amount.setStyleSheet(f"color:{tokens()['text_faint']};")
            self.bal_note.setText("还没取到，点右边「刷新」看一眼")
        elif balance.get("no_api"):
            self.bal_amount.setText("—")
            self.bal_amount.setStyleSheet(f"color:{tokens()['text_faint']};")
            self.bal_note.setText(f"{balance.get('name', '?')} 没有余额接口")
        else:
            sign = symbol(balance.get("currency", ""))
            self.bal_amount.setText(f"{sign}{pet._display_amount():.2f}")
            self.bal_amount.setStyleSheet("")
            self.bal_note.setText(
                f"来源：{balance.get('name', '?')}，今日已用 "
                f"{sign}{(balance.get('today') or 0.0):.2f}")

    # ---------------- 余额和用量 ----------------
    def _page_balance(self, page):
        pet = self.pet
        has_key = self._has_key()
        card = page.card("现在的余额", "配好 Key 才会出来数", "nav.balance")
        self.bal_amount = QLabel("—")
        self.bal_amount.setObjectName("big")
        self.bal_amount.setStyleSheet(f"color:{tokens()['text_faint']};")
        card.addWidget(self.bal_amount)
        self.bal_note = QLabel("")
        self.bal_note.setObjectName("muted")
        card.addWidget(self.bal_note)
        page.row(card, "余额常显", "不收起余额气泡，一直挂着",
                 Switch(pet.balance_always, pet.set_balance_always))
        page.buttons(card, [
            ("刷新", lambda: pet.refresh_balance(silent=False), "primary"),
        ])

        card = page.card("余额来源", "换来源会重新取一次数", "nav.balance")
        page.combo(card, "看谁的余额", "DeepSeek，或你自己加的服务",
                   [(name, name) for name in self._source_names()],
                   pet.cfg.get("balance_source") or "DeepSeek",
                   lambda name: self._run(pet.set_balance_source, name))
        page.row(card, "API Key",
                 "当前：已配置" if has_key else "当前：还没配，配了才看得到余额",
                 self._text_button("换一个…" if has_key else "现在配…",
                                   lambda: self._run(pet._set_key_dialog),
                                   "primary"))
        page.buttons(card, [
            ("添加其他 API Key…",
             lambda: self._run(pet.add_other_key_dialog), None),
            ("删除其他 API Key…",
             lambda: self._run(pet.remove_other_key_dialog), "danger"),
        ])

        card = page.card("今日已用怎么算", "按余额差值算出来的，跟平台可能对不上",
                         "page.calibrate")
        page.row(card, f"每轮对话后显示消耗（当前：{pet.agent_name}）",
                 f"读 {pet.agent_name} 的会话日志，算这一轮用掉多少",
                 Switch(pet.turn_cost_on, pet.set_turn_cost))
        page.row(card, "去哪个文件夹读对话记录", str(pet.agent_dir),
                 self._pair_buttons(
                     ("名称…", lambda: self._run(pet.set_agent_name_dialog)),
                     ("日志目录…", lambda: self._run(pet.set_agent_dir_dialog))))
        page.divider(card)
        page.row(card, "校准今日已用", "按平台用量页对一次数",
                 self._text_button("校准…",
                                   lambda: self._run(pet.calibrate_usage_dialog),
                                   "primary"))

    # ---------------- 天气与城市 ----------------
    def _page_weather(self, page):
        pet = self.pet
        card = page.card("城市", "点一下切过去", "nav.weather")
        current = pet.cfg.get("city", "汕头")
        cities = [c for c in (pet.cfg.get("city_list") or []) if c]
        if current not in cities:
            cities.append(current)
        card.addWidget(Segmented([(c, c) for c in cities], current,
                                 lambda name: self._run(pet._apply_city, name)))
        page.buttons(card, [
            ("手动输入…", lambda: self._run(pet.set_city_dialog), "primary"),
            ("自动定位（按 IP）", lambda: self._run(pet.auto_locate_city), None),
            ("添加城市（联网搜索）",
             lambda: self._run(pet.search_city_dialog), None),
        ])
        if len(cities) > 1:
            page.buttons(card, [
                ("从列表里删掉城市…",
                 lambda: self._run(pet.remove_city_dialog), "danger")])
        page.hint(card, "挂梯子时按 IP 定位会不准，最好手动填。"
                        "想看一眼现在几度：右键桌宠 →「查看天气」。")

    # ---------------- 音乐与歌词 ----------------
    def _page_music(self, page):
        pet = self.pet
        card = page.card("联动", "放歌时桌宠会看着", "nav.music")
        page.row(card, "放歌时看着", "放 QQ音乐 / 网易云 时联动",
                 Switch(pet.music_on, pet.set_music_link))
        page.row(card, "显示歌词内容", "关掉只报歌名",
                 Switch(pet.music_lyrics, pet.set_music_lyrics))
        # 网易云那个播放器拿不到歌词（只有歌名），别让人一直等歌词
        page.hint(card, "网易云暂不支持歌词显示（只有 QQ音乐 能看到歌词）。")
        page.hint(card, "想看一眼在放什么：右键桌宠 →「看一眼在放什么」。")

        card = page.card("歌词对不上？", "跟播放器显示的时间对齐最准", "page.clock")
        page.combo(card, "歌词比音乐早还是晚", "对不上就先在这儿选一档",
                   [(off, label) for label, off
                    in (self.ctx.get("LYRIC_OFFSET_LEVELS") or [])],
                   pet.lyric_offset,
                   lambda off: self._run(pet.set_lyric_offset, off))
        page.buttons(card, [
            ("往前赶 0.5 秒", lambda: pet.nudge_lyric(0.5), None),
            ("往后压 0.5 秒", lambda: pet.nudge_lyric(-0.5), None),
            ("按播放器时间对齐…",
             lambda: self._run(pet.align_lyric_dialog), "primary"),
            ("清零", lambda: pet.nudge_lyric(0.0, True), None),
        ])

    # ---------------- 形象与外观 ----------------
    def _page_appearance(self, page):
        pet = self.pet
        skin_pet = self.ctx.get("SKIN_PET", "大肥鱼")
        skin_widget = self.ctx.get("SKIN_WIDGET", "小鲸鱼挂件")
        card = page.card("形象", "换形象、上传自己的图", "nav.appearance")
        page.row(card, "现在是谁", "",
                 Segmented([(skin_pet, f"{skin_pet}（三视图）"),
                            (skin_widget, f"{skin_widget}（单张）")],
                           pet.skin, lambda name: self._run(pet.set_skin, name)))
        n_pet = len(pet.skin_library("pet"))
        n_widget = len(pet.skin_library("widget"))
        page.buttons(card, [
            (f"我的形象库…（三维 {n_pet} · 挂件 {n_widget}）",
             lambda: self._run(pet.skin_library_dialog), "primary"),
            ("全部恢复默认形象",
             lambda: self._run(pet.clear_custom_skin, None), "danger"),
        ])

        card = page.card("大小", "脚底和中心不动，原地缩放", "page.resize")
        levels = list((self.ctx.get("SIZE_LEVELS") or {}).items())
        self.size_levels = levels
        current_level = None
        for _label, mult in levels:
            if abs(getattr(pet, "cur_h", 0) - 340 * mult) < 2:
                current_level = mult
        # 档位和滑块是同一个大小：点档位 → 滑块跳过去；拖滑块停在哪一档 → 那一档点亮
        self.size_seg = Segmented([(mult, label) for label, mult in levels],
                                  current_level, self._on_size_level)
        page.row(card, "档位", "常用五档，点一下滑块就跟着跳过去",
                 self.size_seg)
        lo = self._size_pct(self.ctx.get("SIZE_MIN", 0.30))
        hi = self._size_pct(self.ctx.get("SIZE_MAX", 1.20))
        now = self._size_pct(pet.cfg.get("size", 0.72))
        self.size_slider = page.slider(
            card, "精确调节", f"{lo}% ~ {hi}%，跟上面的档位是同一个大小",
            lo, hi, min(max(now, lo), hi), "%", self._on_size_percent)

        card = page.card("外观", "", "page.opacity")
        page.slider(card, "透明度", "拖太低就快看不见了", 20, 100,
                    int(pet.opacity * 100), "%",
                    lambda v: self._run(pet.set_opacity, v / 100.0))
        page.row(card, "窗口层级", "跟别的窗口谁在前", self._layer_combo())
        page.row(card, "拖拽吸附四边", "拖到屏幕边上自己贴住",
                 Switch(pet.snap_on, pet.set_snap))
        page.row(card, "左吸附时翻面", "贴在左边时面朝屏幕里",
                 Switch(pet.flip_on_left, pet.set_flip_on_left))

    # ---------------- 行为与互动 ----------------
    def _page_behavior(self, page):
        pet = self.pet
        card = page.card("模式", "它平时怎么动", "nav.behavior")
        page.row(card, "怎么走", "",
                 Segmented([("wander", "自由散步"), ("follow", "跟随鼠标"),
                            ("still", "原地待着")],
                           pet.mode, lambda key: self._run(pet.set_mode, key)))
        page.row(card, "原地待着时也跟着鼠标转", "只转头、不挪窝",
                 Switch(pet.still_face_cursor, pet.set_still_face_cursor))

        card = page.card("快速双击", "双击它一下会做什么", "ui.spinner")
        choices = list(self.ctx.get("DOUBLE_CLICK_CHOICES") or [])
        page.combo(card, "双击效果", "没配 Key 时选不了「看一眼余额」",
                   [(k, label) for k, label in choices],
                   pet._double_click_choice(),
                   lambda key: self._run(pet.set_double_click, key))
        page.buttons(card, [
            ("改写这几句台词…",
             lambda: self._run(pet.edit_lines_dialog, "DOUBLE_CLICK_LINES"),
             None)])

        card = page.card("防误触", "按住它拖不动、点不到它", "page.lock")
        page.row(card, "锁定位置", "拖不动，点击 / 双击照常",
                 Switch(pet.locked, pet.set_locked))
        page.row(card, "鼠标穿透", "点不到它（托盘图标能解除）",
                 Switch(pet.cfg.get("passthrough", False), pet.set_passthrough))
        page.hint(card, "真点不到它了：双击托盘图标，或去「通用」里点救急恢复。")

    # ---------------- 文案与语录 ----------------
    def _page_lines(self, page):
        pet = self.pet
        card = page.card("高峰 / 空闲时段", "DeepSeek 不同时段价钱不一样",
                         "nav.lines")
        page.row(card, "在气泡里标出现在贵不贵", "显示现在是高峰还是空闲",
                 Switch(pet.show_peak, pet.set_show_peak))
        page.combo(card, "这两句怎么写", "换个说法",
                   [(name, name) for name
                    in (self.ctx.get("PEAK_TEXT_STYLES") or {})],
                   pet.peak_style,
                   lambda style: self._run(pet.set_peak_style, style))

        card = page.card("语录", "闲着时它自己冒话", "ui.spinner")
        levels = list((self.ctx.get("LINE_FREQ_LEVELS") or {}).items())
        page.combo(card, "说话频率", "太吵就调安静一点",
                   [(name, f"{name}（{conf.get('hint', '')}）")
                    for name, conf in levels],
                   pet.line_freq,
                   lambda name: self._run(pet.set_line_freq, name))
        n_custom = len(pet.cfg.get("custom_lines") or {})
        page.row(card, "台词内容",
                 f"自己写 / 改写内置（已改 {n_custom} 类）" if n_custom
                 else "自己写 / 改写内置",
                 self._text_button("打开编辑器…",
                                   lambda: self._run(pet.edit_lines_dialog),
                                   "primary"))

    # ---------------- 音效 ----------------
    def _page_sound(self, page):
        pet = self.pet
        card = page.card("音效", "点击 / 拖拽时的那一声", "nav.sound")
        page.row(card, "按键音效", "关掉就安静了",
                 Switch(pet.sound_on, pet.set_sound))
        page.combo(card, "音效选择", "内置几套，也可以自己加",
                   [(name, name) for name in pet._sound_names()],
                   pet.sound_set,
                   lambda name: self._run(pet.set_sound_set, name))
        page.slider(card, "音量", "", 0, 100, int(pet.volume * 100), "%",
                    lambda v: self._run(pet.set_volume, v / 100.0))
        page.buttons(card, [
            ("试听", lambda: pet.preview_sounds(), "primary"),
            ("添加我的音效…",
             lambda: self._run(pet.add_custom_sound_dialog), None),
            ("删掉我加的音效…",
             lambda: self._run(pet.remove_custom_sound_dialog), "danger"),
        ])

    # ---------------- 联动与自动化 ----------------
    def _page_integration(self, page):
        pet = self.pet
        card = page.card("打开应用时冒泡", "它看着你开什么，顺口吐槽两句",
                         "nav.integration")
        page.row(card, "打开应用时冒泡", "扫一遍本机应用，挑几个给它管",
                 Switch(pet.process_alerts, pet.set_process_alerts))
        page.buttons(card, [
            ("扫描电脑应用并添加…",
             lambda: self._run(pet.scan_apps_dialog), "primary"),
            ("清理自定义 / 改写的文字…",
             lambda: self._run(pet.remove_custom_app_dialog), "danger"),
        ])
        page.hint(card, "扫出来的每个应用都能单独改台词，改错了可以在这儿清掉。")

    # ---------------- 性能与工具 ----------------
    def _page_performance(self, page):
        pet = self.pet
        card = page.card("流畅度", "动画优先还是省资源", "nav.performance")
        page.row(card, "怎么跑", "",
                 Segmented([(True, "性能模式 · 动画优先"),
                            (False, "休闲模式 · 省资源")],
                           pet.perf_mode,
                           lambda on: self._run(pet.set_perf_mode, on)))

        card = page.card("百宝箱 · 回收内存",
                         "把后台程序用不着的内存先还给系统", "page.sparkle")
        page.row(card, "回收时不动前台程序", "防止你正在用的一下子卡住",
                 Switch(pet.cfg.get("mem_skip_foreground", True),
                        pet.set_mem_skip_foreground))
        last = getattr(pet, "_mem_last", None)
        human = self.ctx.get("human_mb", lambda n: f"{n / 1048576:.0f} MB")
        page.hint(card,
                  f"上次：{last[0]} 个程序腾出 {human(last[1])}" if last
                  else "还没收过。第一把通常收得最多，紧接着再点往往只剩零头。",
                  "muted")
        page.buttons(card, [("回收内存", lambda: pet.mem_trim_now(), "primary")])

    # ---------------- 通用 ----------------
    def _page_general(self, page):
        pet = self.pet
        card = page.card("显示", "", "nav.general")
        page.buttons(card, [
            ("显示 / 隐藏", lambda: pet.toggle_visible(), "primary"),
            ("回到屏幕内", lambda: pet.snap_into_screen(), None),
            ("救急恢复", lambda: pet.force_recover(), None),
        ], align_right=False)

        card = page.card("开机", "", "nav.general")
        page.row(card, "开机自启", "下次开机自己出来",
                 Switch(pet.cfg.get("autostart", False), pet.set_autostart))
        page.hint(card, "自启是在「启动」文件夹里放一个快捷方式，随时关得掉。")

        card = page.card("主题", "默认跟着 Windows 的亮暗走", "page.theme-system")
        seg = Segmented(THEME_MODES, self._mode, self.set_theme)
        self.theme_seg = seg
        page.row(card, "界面配色", "亮色 / 暗色 / 跟系统",
                 seg)
        page.hint(card, "「跟随系统」会在你切 Windows 深色模式时自动跟着变。")

        card = page.card("排查问题", "右键菜单不听话的时候才用得上", "ui.help")
        page.row(card, "记录菜单日志", "会写一个 menu-debug.log 方便查",
                 Switch(bool(pet.cfg.get("menu_debug", False)),
                        lambda on: pet.set_menu_debug(on)))
        page.divider(card)
        page.row(card, "右键菜单用经典版",
                 "打开后右键弹的是旧版那份完整菜单（功能全，但很长）",
                 Switch(bool(pet.cfg.get("classic_menu", False)),
                        pet.set_classic_menu))
        page.buttons(card, [
            ("打开经典菜单…（旧版那份长菜单）",
             lambda: self._run(pet._open_classic_menu), None)])

        card = page.card("最小化动画", "窗口最小化时往哪儿收", "page.resize")
        page.row(card, "落点",
                 "默认落在任务栏中间；想对准任务栏上自己那个图标就校准一次",
                 self._text_button("校准…", self._calibrate_min_target))
        saved = pet.cfg.get("minimize_target")
        self._cal_hint = page.hint(
            card,
            (f"现在记的是：({int(saved[0])}, {int(saved[1])})"
             if isinstance(saved, (list, tuple)) and len(saved) == 2
             else "还没校准 —— 动画会落在任务栏正中间。"),
            "muted")

    # ---------------- 关于 ----------------
    def _page_about(self, page):
        card = page.card("大肥鱼桌宠", "Windows 桌面宠物", "nav.about")
        head = QHBoxLayout()
        head.setSpacing(12)
        logo = QLabel()
        logo.setFixedSize(56, 56)
        logo.setPixmap(self._logo_pixmap(56))
        head.addWidget(logo)
        col = QVBoxLayout()
        col.setSpacing(2)
        name = QLabel("大肥鱼桌宠")
        name.setObjectName("cardTitle")
        col.addWidget(name)
        ver = QLabel(f"版本 v{APP_VERSION}")
        ver.setObjectName("muted")
        col.addWidget(ver)
        col.addStretch(1)
        head.addLayout(col)
        head.addStretch(1)
        card.addLayout(head)
        page.hint(card, "显示 DeepSeek 余额、天气、正在放的歌与歌词；"
                        "能换形象、带音效、可开机自启。")
        page.buttons(card, [
            ("项目主页", lambda: self._open_url(GITHUB_URL), "primary"),
            ("反馈 / 提需求",
             lambda: self._open_url(GITHUB_URL + "/issues"), None),
        ], align_right=False)

    # ---------------- 小工具 ----------------
    def _size_pct(self, mult):
        """倍率 → 滑块上的百分比（桌宠那边算，界面这边只负责显示）。"""
        fn = self.ctx.get("size_percent")
        if fn is not None:
            try:
                return int(fn(mult))
            except Exception:
                pass
        try:
            return int(round(float(mult) * 100))
        except (TypeError, ValueError):
            return 100

    def _mult_from_pct(self, pct):
        fn = self.ctx.get("size_from_percent")
        if fn is not None:
            try:
                return float(fn(pct))
            except Exception:
                pass
        return float(pct) / 100.0

    def _on_size_level(self, mult):
        """点了某个档位：先改大小，再把滑块挪到同一个百分比上。"""
        self._run(self.pet.set_size, mult)
        bar = getattr(self, "size_slider", None)
        if bar is None:
            return
        pct = self._size_pct(mult)
        if bar.value() != pct:
            bar.blockSignals(True)          # 别让 setValue 再回调一次
            bar.setValue(pct)
            bar.blockSignals(False)
        label = getattr(bar, "value_label", None)
        if label is not None:
            label.setText(f"{pct}%")

    def _on_size_percent(self, pct):
        """拖滑块：改大小，并且"停在某一档上"时把那一档点亮。"""
        self._run(self.pet.set_size, self._mult_from_pct(pct))
        seg = getattr(self, "size_seg", None)
        if seg is None:
            return
        hit = None
        for _label, mult in getattr(self, "size_levels", []):
            if self._size_pct(mult) == pct:
                hit = mult
                break
        seg.set_value(hit)                  # 没停在任何一档上就把整排取消选中

    def _sync_size_controls(self):
        """从配置里读一次大小，把档位和滑块都摆对（别的地方改过大小也追得上）。"""
        if not hasattr(self, "size_slider"):
            return
        pct = self._size_pct(self.pet.cfg.get("size", 0.72))
        bar = self.size_slider
        if bar.value() != pct:
            bar.blockSignals(True)
            bar.setValue(pct)
            bar.blockSignals(False)
        if hasattr(bar, "value_label"):
            bar.value_label.setText(f"{pct}%")
        seg = getattr(self, "size_seg", None)
        if seg is not None:
            hit = None
            for _label, mult in getattr(self, "size_levels", []):
                if self._size_pct(mult) == pct:
                    hit = mult
                    break
            seg.set_value(hit)

    def _run(self, fn, *args, **kwargs):
        """界面上的动作统一入口：抛异常别把窗口带崩，也别吃掉消息。"""
        try:
            return fn(*args, **kwargs)
        except Exception as exc:
            print("控制台动作失败:", exc)
            return None

    def _open_url(self, url):
        try:
            from PySide6.QtCore import QUrl
            from PySide6.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(url))
        except Exception:
            pass

    def _has_key(self):
        try:
            return bool(self.pet._current_source()[1])
        except Exception:
            return False

    def _source_names(self):
        names = ["DeepSeek"]
        for item in (self.pet.cfg.get("other_keys") or []):
            name = item.get("name")
            if name and name not in names:
                names.append(name)
        return names

    def _text_button(self, text, slot, style=None):
        btn = QPushButton(text)
        btn.setFixedHeight(32)
        if style:
            btn.setObjectName(style)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(lambda _=False: slot())
        return btn

    def _pair_buttons(self, *pairs):
        wrap = QWidget()
        line = QHBoxLayout(wrap)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(8)
        for text, slot in pairs:
            line.addWidget(self._text_button(text, slot))
        return wrap

    def _layer_combo(self):
        labels = self.ctx.get("LAYER_LABELS") or {"top": "置顶"}
        box = QComboBox()
        for key, label in labels.items():
            box.addItem(label, key)
        for index in range(box.count()):
            if box.itemData(index) == self.pet.layer:
                box.setCurrentIndex(index)
                break
        box.setCursor(Qt.CursorShape.PointingHandCursor)
        box.currentIndexChanged.connect(
            lambda _i: self._run(self.pet.set_layer, box.currentData()))
        return box

    # ---------------- 窗口事件 ----------------
    def minimize_with_anim(self):
        """最小化：照着 Windows 那套"整窗缩到任务栏"的感觉做一遍。

        关键是**等比缩放**，不是把窗口越改越小：改小窗口的话，里面的字和控件会跟着重新排版，
        看着像"往下划拉"。所以先把窗口拍成一张图，动画期间只画这张图、把系统那套控件藏起来
        （`self.shell.hide()`），窗口一缩这张图就整体跟着缩 —— 跟 Windows 最小化一个观感。

        收完再**真正 minimize**（任务栏图标还在，点一下能还原）。
        """
        if self.isMinimized():
            return
        if getattr(self, "_anim_target", None) == "min":
            return                       # 已经在往最小化走，别重复起
        if getattr(self, "_min_pm", None) is None:
            self._min_pm = self.grab()   # 素材：整窗截图（还原动画也用它）
        self._restoring = False
        self.shell.hide()                # 动画期间只画那张截图
        geo = self.geometry()
        # 只有"手里没动画、也不是半路接回来的"才更新这个基准 ——
        # 不然连点时会把动画中间那个尺寸当成"正常大小"记下来，
        # 后面还原就会停在一个不上不下的大小上（连点 bug 的来源之一）。
        if (getattr(self, "_min_anim", None) is None
                and not getattr(self, "_restoring", False)):
            self._restore_geo = geo
        # 窗口平时有最小尺寸（820x560，免得被拖得太小），但动画要缩到任务栏那么点大，
        # 所以先把下限松开 —— 不松的话 Qt 会把几何钳在 820x560，
        # 看着就只剩"往下划拉"了（这坑真踩过）
        self._min_min_size = self.minimumSize()
        self.setMinimumSize(0, 0)
        self.update()
        self._start_anim(going_min=True)

    def _start_anim(self, going_min, force_from=None):
        """起一段动画。**可以被打断**：手里要是有正在跑的，先停掉，
        从"现在这个大小 / 现在这个透明度"接着往新方向走（跟 Windows 一样是接管，
        不是忽略新请求、也不是跳回去重头再来）。

        这里**不用** Qt 的 QPropertyAnimation：它跑在全局统一计时器上（≈60fps），
        同一段时长帧数只有一半。改成自己按 `ANIM_TICK_MS`（8ms ≈120fps）插值，
        时间不变、帧数翻倍，掉帧也更容易补上。
        """
        self._stop_anim()
        normal = getattr(self, "_restore_geo", None) or self.geometry()
        small = self._minimize_end_rect(normal)
        # force_from：有些路径（从最小化里出来）show() 之后 Qt 会把"原来的几何"用回去，
        # 这时候不能信 self.geometry()，否则动画就从满尺寸起步 —— 那一帧就是闪大窗口
        cur_geo = force_from if force_from is not None else self.geometry()
        cur_op = getattr(self, "_anim_fade", 1.0)
        self._anim = {
            "t0": time.perf_counter(),
            "dur": max(0.05, MINIMIZE_ANIM_MS / 1000.0),
            "from": QRect(cur_geo),
            "to": QRect(small if going_min else normal),
            "fade0": cur_op,
            "fade1": 0.0 if going_min else 1.0,
            "going_min": going_min,
        }
        self._min_anim = self                    # 外面拿它当"动画在跑"的标记（.stop() 也有）
        self._anim_target = "min" if going_min else "restore"
        if self._tick_timer is None:
            self._tick_timer = QTimer(self)
            self._tick_timer.setTimerType(Qt.TimerType.PreciseTimer)
            self._tick_timer.timeout.connect(self._anim_tick)
        self._tick_timer.start(ANIM_TICK_MS)
        self._anim_tick()                    # 立刻走第一拍，别等 8ms

    def stop(self):
        """给外面看的：答应"能 stop()"这个接口（_start_anim 里会调）。"""
        self._stop_anim()

    def _stop_anim(self):
        if self._tick_timer is not None:
            self._tick_timer.stop()
        self._anim = None
        self._min_anim = None
        self._anim_target = None

    def _anim_tick(self):
        """动画的一拍：按真实流逝时间算进度，所以掉一两帧也不会变慢。"""
        a = self._anim
        if not a:
            self._stop_anim()
            return
        p = (time.perf_counter() - a["t0"]) / a["dur"]
        p = 0.0 if p < 0.0 else (1.0 if p > 1.0 else p)
        # InCubic / OutCubic，和原来一致
        e = p ** 3 if a["going_min"] else 1.0 - (1.0 - p) ** 3
        f, t = a["from"], a["to"]
        geo = QRect(int(f.x() + (t.x() - f.x()) * e),
                    int(f.y() + (t.y() - f.y()) * e),
                    int(f.width() + (t.width() - f.width()) * e),
                    int(f.height() + (t.height() - f.height()) * e))
        self.setGeometry(geo)
        self._anim_fade = a["fade0"] + (a["fade1"] - a["fade0"]) * e
        self.update()
        if p >= 1.0:
            going_min = a["going_min"]
            self._stop_anim()
            self._anim_done(going_min)

    def _anim_done(self, going_min):
        self._anim_target = None
        if going_min:
            self._minimize_done(getattr(self, "_restore_geo", None) or self.geometry())
        else:
            self._finish_restore()

    def _minimize_target(self):
        """最小化动画往哪儿收。

        理想是"缩到任务栏上我自己那个按钮"—— 但那个按钮在 Windows 11 上是 XAML 画的，
        拿不到它的矩形（试过两条路：.NET UIA 查询要 15~50 秒还查不到；
        MSAA 命中测试在任务栏上返回的是前台窗口的元素）。所以做成**可校准**：
        「通用」页里点一下校准，把鼠标停在任务栏那个图标上，记下来当落点。
        """
        saved = self.pet.cfg.get("minimize_target")
        if isinstance(saved, (list, tuple)) and len(saved) == 2:
            try:
                return QPoint(int(saved[0]), int(saved[1]))
            except (TypeError, ValueError):
                pass
        full = (self.screen() or QApplication.primaryScreen()).geometry()
        return QPoint(full.center().x(), full.bottom() - 10)

    def _minimize_end_rect(self, from_geo):
        """最小化动画的终点矩形（按 from_geo 的 1/8 缩，落在 _minimize_target() 上）。"""
        small = QRect(0, 0,
                      max(46, from_geo.width() // 8),
                      max(34, from_geo.height() // 8))
        small.moveCenter(self._minimize_target())
        return small

    def restore_with_anim(self):
        """从任务栏点回来：把最小化动画**倒着放一遍** —— 从落点那一点点大，一边放大一边淡进来。

        系统和最小化一样不给这种窗口跑动画（分层窗口），所以要自己来：
        素材就是最小化时留下的那张整窗截图。
        """
        if getattr(self, "_anim_target", None) == "restore":
            return                       # 已经在往还原走了
        if not self.isMinimized() and getattr(self, "_min_pm", None) is None:
            # 正常开着、也没素材：谈不上"从任务栏还原"，抬到前面就行
            self.showNormal()
            self.raise_()
            self.activateWindow()
            return
        shot = getattr(self, "_min_pm", None)
        if not self.isMinimized() and (shot is None or shot.isNull()):
            self._finish_restore()          # 没素材（没走我们的最小化）：直接还原
            return
        # 打断最小化动画（窗口还没真最小化）时，什么都不用摆，直接从当前位置往回走
        if self.isMinimized():
            normal = getattr(self, "_restore_geo", None) or self.geometry()
            small = self._minimize_end_rect(normal)
            # 顺序有讲究（不然会闪一下大的）：
            #   ① 先 hide（脱离最小化）→ ② 清掉最小化状态 → ③ 隐身 →
            #   ④ 摆到落点那么小 → ⑤ show
            # 反过来（先 showNormal 再挪）中间会有一帧停在"原来那么大"上 —— 那就是闪烁。
            # 另外 changeEvent 里那条兜底是"没在放动画又脱离最小化 → 收拾干净"，
            # 这里先举个牌子，别让它把我正在建的动画对象清掉。
            self._restoring = True
            self.hide()
            # hide() 不会把"最小化"这个状态清掉 —— 不清的话下面 show() 回来
            # 窗口还是最小化的（等于还原白做了）
            self.setWindowState(Qt.WindowState.WindowNoState)
            self._anim_fade = 0.0
            self.setMinimumSize(0, 0)
            self.setGeometry(small)
            self.show()
            # show() 之后再钉一次：Qt 有时会在这一步把窗口摆回它记住的几何
            self.setGeometry(small)
            self._start_anim(going_min=False, force_from=small)
            self.update()
            return
        else:
            # 从"正在缩小"半路接回来：把最小尺寸松开就行，剩下的交给 _start_anim
            self._restoring = True
            self.setMinimumSize(0, 0)
        self.update()
        self._start_anim(going_min=False)

    def _finish_restore(self):
        """还原收尾：把真控件显示回来、清掉那张素材图、状态复位。"""
        if getattr(self, "_anim_target", None) == "min":
            return          # 正往最小化走，别把真控件放出来（那一帧会闪）
        self._min_anim = None
        self._restoring = False
        try:
            if getattr(self, "_min_min_size", None):
                self.setMinimumSize(self._min_min_size)
            self._min_pm = None
            self.shell.show()
            self._anim_fade = 1.0
            self.update()
            self.raise_()
            self.activateWindow()
        except Exception:
            pass

    def restore_or_show(self):
        """从菜单「打开设置…」进来：最小化着就先播还原动画，否则抬到前面。"""
        if self.isMinimized():
            self.restore_with_anim()
            return
        self.show()
        self.raise_()
        self.activateWindow()

    def _minimize_done(self, restore_geo):
        """动画收尾：把窗口和控件还原（这会儿还是全透明的，看不见），再真正最小化。"""
        self._min_anim = None
        try:
            self.setGeometry(restore_geo)
            if getattr(self, "_min_min_size", None):
                self.setMinimumSize(self._min_min_size)
            # 摆大小这一下必须是全透明的（否则会闪出一帧大窗口），稳一手再最小化
            self._anim_fade = 0.0
            # 注意：这里**不清** `_min_pm`、也不把 shell 显示回来 ——
            # 那张整窗截图留着当"还原动画"的素材（从任务栏点回来时反向放一遍）。
            # 万一窗口被系统自己还原了，changeEvent 里那条兜底会把状态收拾干净。
            # 这一下是我们自己按下去的：打上标记，免得下面 changeEvent 里
            # 的兜底逻辑又把窗口拽回来重放一遍动画
            self._min_self = True
            self.showMinimized()
        except Exception:
            pass
        # 注意：**这里不要把不透明度放回 1.0**。
        # showMinimized() 是异步的，紧接着恢复不透明的话，窗口在真正最小化之前
        # 还会在屏幕上待一帧 —— 那一帧就是满尺寸 + 全不透明的"闪一下"
        # （采集日志实测：t=10.651 满尺寸 + 透明=1.0 + 最小化=1）。
        # 留着全透明不管，等还原动画（或 _finish_restore）需要显示时再放回去。

    def paintEvent(self, _ev):
        """自己画一圈柔和阴影。

        原来用的是 `QGraphicsDropShadowEffect`：它会把整棵子树先画进一张离屏图再贴出来，
        配"无边框 + 半透明"的窗口时，子控件一重绘（比如按钮 hover）就容易留残影 ——
        表现成"某条边像被什么挡了一块"。自己画几圈半透明圆角矩形就没有这个问题。

        阴影**画一次缓存成图**：不然每滚一帧都要重画 7 圈抗锯齿圆角矩形，快速滚动会掉帧。
        """
        painter = QPainter(self)
        shot = getattr(self, "_min_pm", None)
        if shot is not None:
            # 最小化动画进行中：把这帧"整窗截图"按当前窗口大小等比铺上去，
            # 于是看起来就是整只窗口在缩小（里面的字和控件不会重排）
            # 注意用 FastTransformation：平滑缩放一张上千像素的图，每帧要十几毫秒，
            # 动画就会一顿一顿的（"掉帧卡顿"就是这么来的）
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
            painter.setOpacity(max(0.0, min(1.0, getattr(self, "_anim_fade", 1.0))))
            painter.drawPixmap(self.rect(), shot)
        else:
            painter.drawPixmap(0, 0, self._shadow_pixmap())
        painter.end()

    def _on_fade(self, value):
        """淡入淡出的每一拍：只更新一个数 + 重画，不去动窗口属性。"""
        try:
            self._anim_fade = float(value)
        except (TypeError, ValueError):
            return
        self.update()

    def _shadow_pixmap(self):
        """窗口阴影：同一尺寸 / 同一主题只画一次，之后都是贴图。"""
        key = (self.width(), self.height(), tokens()["shadow"].name(),
               tokens()["shadow"].alpha(), self.devicePixelRatioF())
        if getattr(self, "_shadow_key", None) == key and self._shadow_pm is not None:
            return self._shadow_pm
        dpr = self.devicePixelRatioF() or 1.0
        pm = QPixmap(int(self.width() * dpr), int(self.height() * dpr))
        pm.fill(Qt.GlobalColor.transparent)
        pm.setDevicePixelRatio(dpr)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(Qt.PenStyle.NoPen)
        shadow = QColor(tokens()["shadow"])
        base = QRectF(self.shell.geometry())
        for step in range(6, 0, -1):
            color = QColor(shadow)
            color.setAlpha(max(3, int(shadow.alpha() * (1.0 - step / 7.0) * 0.62)))
            painter.setBrush(color)
            painter.drawRoundedRect(
                base.adjusted(-step, -step + 3, step, step + 3),
                14 + step, 14 + step)
        painter.end()
        self._shadow_pm = pm
        self._shadow_key = key
        return pm

    def closeEvent(self, ev):
        self._live.stop()
        super().closeEvent(ev)

    def changeEvent(self, ev):
        """兜底：万一原生消息那条路没拦到（别的入口进来的最小化），也走我们的动画。"""
        if ev.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized():
                if getattr(self, "_min_self", False):
                    self._min_self = False      # 自己发起的那一次，放行
                else:
                    QTimer.singleShot(0, self._minimize_from_system)
            elif (getattr(self, "_min_pm", None) is not None
                    and getattr(self, "_min_anim", None) is None
                    and not getattr(self, "_restoring", False)):
                # 窗口被系统自己还原了：别把那张旧截图留在屏幕上，收拾干净
                QTimer.singleShot(0, self._finish_restore)
        super().changeEvent(ev)

    def _minimize_from_system(self):
        """系统那边把窗口最小化了（而我们没拦到）：先还原，再走自己的动画。"""
        if getattr(self, "_min_anim", None) is not None:
            return
        try:
            self.showNormal()
        except Exception:
            return
        self.minimize_with_anim()

    def _calibrate_min_target(self):
        """校准最小化动画的落点。

        点一下开始：鼠标移到自己那个任务栏图标上，**按空格**就记现在这一点
        （按 Enter 也行；不想按就 8 秒后自动记下当时鼠标在哪）。
        再点一次这颗按钮 = 也是"就记这儿"。
        """
        if getattr(self, "_cal_timer", None) is not None:
            self._capture_min_target()          # 已经在等 → 这一下就是"就记这儿"
            return
        self._cal_left = 8.0
        self._cal_timer = QTimer(self)
        self._cal_timer.setInterval(100)
        self._cal_timer.timeout.connect(self._cal_tick)
        self._cal_timer.start()
        self._cal_tick()

    def _cal_tick(self):
        self._cal_left -= 0.1
        pos = QCursor.pos()
        if self._cal_left <= 0:
            self._capture_min_target()
            return
        self._set_cal_hint(
            f"鼠标现在在 ({pos.x()}, {pos.y()}) —— 停到任务栏上你自己那个图标上，"
            f"按空格记住（{self._cal_left:.0f} 秒后自动记）")

    def _capture_min_target(self):
        timer = getattr(self, "_cal_timer", None)
        if timer is not None:
            timer.stop()
            self._cal_timer = None
        pos = QCursor.pos()
        self._run(self.pet.set_minimize_target, (pos.x(), pos.y()))
        self._set_cal_hint(f"记下了：({pos.x()}, {pos.y()}) —— 以后最小化就往这儿收")

    def _set_cal_hint(self, text):
        label = getattr(self, "_cal_hint", None)
        if label is not None:
            label.setText(text)

    def keyPressEvent(self, ev):
        if (getattr(self, "_cal_timer", None) is not None
                and ev.key() in (Qt.Key.Key_Space, Qt.Key.Key_Return, Qt.Key.Key_Enter)):
            self._capture_min_target()      # 校准期间按空格 = 就记这儿
            return
        if ev.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(ev)
