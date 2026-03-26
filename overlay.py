#!/usr/bin/env python3
"""
Classroom Overlay Tool
======================
A transparent, always-on-top desktop overlay window built with PyQt6.

Key Features:
  - Frameless, full-screen transparent overlay (click-through background)
  - FloatingPanel windows: draggable, resizable, minimizable, closeable
  - Persistent toolbar at the top for toggling panels and quitting
  - Global minimize: hide everything to a tiny restore button
  - Rich text editor with scrollable formatting toolbar + Ctrl+B/I/U shortcuts
  - Student list panel loaded from JSON class files (collapsible)
  - Timer / Stopwatch panel
  - Random Name Picker + Group Maker panel
  - Traffic Light system (click-cycle + drag-and-drop sort modes)
  - Work Symbols panel (toggle emoji symbols)
  - Noise Monitor panel (live microphone level)
  - Help panel with shortcuts and tips
  - Class selector via toolbar dropdown
  - Saveable/restorable layouts per class (positions, sizes, text content)

Required Libraries:
  pip install PyQt6

Run without console window:
  pythonw overlay.pyw
  OR: python overlay.py  (will show console)
"""

import sys
import os

# Force X11 on Linux (Wayland doesn't support window positioning/dragging)
if sys.platform != "win32" and sys.platform != "darwin":
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

import json
import glob
import math
import random
import shutil
import struct
import time
import wave
import functools
import io as _io
import subprocess
if sys.platform == "win32":
    import ctypes

from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QLabel,
    QTextEdit,
    QComboBox,
    QHBoxLayout,
    QVBoxLayout,
    QScrollArea,
    QFrame,
    QColorDialog,
    QMenu,
    QSpinBox,
    QGridLayout,
    QSlider,
    QProgressBar,
    QMessageBox,
    QLineEdit,
    QSizePolicy,
    QFileDialog,
    QInputDialog,
    QCheckBox,
    QToolTip,
)
from PyQt6.QtCore import (
    Qt, QTimer, QRect, QSize, pyqtSignal, QMimeData,
    QUrl, QEvent,
)
from PyQt6.QtGui import (
    QPainter,
    QColor,
    QKeySequence,
    QShortcut,
    QTextCharFormat,
    QFont,
    QFontMetrics,
    QIcon,
    QTextCursor,
    QDrag,
    QPen,
    QBrush,
    QPixmap,
    QImage,
    QPainterPath,
    QFontDatabase,
)

# Try to import QtMultimedia for noise monitor + video playback
try:
    from PyQt6.QtMultimedia import QAudioSource, QMediaDevices, QAudioFormat, QSoundEffect, QMediaPlayer, QAudioOutput
    HAS_MULTIMEDIA = True
except ImportError:
    HAS_MULTIMEDIA = False

try:
    from PyQt6.QtMultimediaWidgets import QVideoWidget
    HAS_VIDEO_WIDGET = True
except ImportError:
    HAS_VIDEO_WIDGET = False

# Try to import qrcode for QR code generator
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


# ---------------------------------------------------------------------------
# Global scale factor (reference: 1920x1080 = 1.0)
# ---------------------------------------------------------------------------

SCALE_FACTOR = 1.0  # Will be set in main() before OverlayApp is created


def compute_scale_factor():
    """Compute a global UI scale factor based on screen size.
    Reference resolution is 1920x1080 (factor 1.0).
    Clamped to [0.55, 1.0] so things don't get absurdly small or large."""
    screen = QApplication.primaryScreen()
    if screen is None:
        return 1.0
    geo = screen.geometry()
    factor = min(geo.width() / 1920, geo.height() / 1080)
    return max(0.55, min(1.0, factor))


def S(value):
    """Scale a pixel value by the global SCALE_FACTOR. Returns int."""
    return max(1, int(value * SCALE_FACTOR))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@functools.lru_cache(maxsize=1)
def get_base_dir():
    """Return base directory — works both in dev and PyInstaller bundle."""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


@functools.lru_cache(maxsize=1)
def get_classes_dir():
    """Return the path to the 'classes' folder next to this script."""
    return os.path.join(get_base_dir(), "classes")


@functools.lru_cache(maxsize=1)
def get_layouts_dir():
    """Return the path to the 'layouts' folder next to this script."""
    d = os.path.join(get_base_dir(), "layouts")
    os.makedirs(d, exist_ok=True)
    return d


@functools.lru_cache(maxsize=1)
def get_sounds_dir():
    """Return the path to the 'sounds' folder next to this script."""
    d = os.path.join(get_base_dir(), "sounds")
    os.makedirs(d, exist_ok=True)
    return d


def load_class_list(filepath):
    """Load a class JSON file and return (class_name, list_of_students)."""
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)
    class_name = data.get("class_name", "Unknown")
    students = data.get("students", [])
    return class_name, students


def discover_class_files():
    """Return a list of (display_name, filepath) for all class JSON files."""
    classes_dir = get_classes_dir()
    pattern = os.path.join(classes_dir, "*.json")
    files = sorted(glob.glob(pattern))
    result = []
    for fp in files:
        try:
            name, _ = load_class_list(fp)
            result.append((f"Klasse {name}", fp))
        except (json.JSONDecodeError, KeyError):
            basename = os.path.basename(fp)
            result.append((basename, fp))
    return result


def clear_layout(layout):
    """Removes all widgets from a layout, detaching them from their parent."""
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.setParent(None)


# ---------------------------------------------------------------------------
# Shared stylesheet constants
# ---------------------------------------------------------------------------

CARD_BG = "rgba(30, 30, 30, 220)"
CARD_BORDER = "rgba(255, 255, 255, 60)"


def _toolbar_button_style():
    return """
    QPushButton {
        background-color: rgba(60, 60, 60, 220);
        color: white;
        border: 1px solid rgba(255, 255, 255, 60);
        border-radius: 4px;
        padding: 5px 12px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: rgba(80, 80, 80, 230);
    }
    QPushButton:pressed {
        background-color: rgba(40, 40, 40, 255);
    }
    QPushButton:checked {
        background-color: rgba(0, 120, 215, 220);
        border: 1px solid rgba(0, 150, 255, 200);
    }
    QPushButton:disabled {
        background-color: rgba(50, 50, 50, 150);
        color: rgba(255, 255, 255, 80);
        border: 1px solid rgba(255, 255, 255, 30);
    }
"""


def _format_button_style():
    return """
    QPushButton {
        background-color: rgba(70, 70, 70, 220);
        color: white;
        border: 1px solid rgba(255, 255, 255, 80);
        border-radius: 5px;
        padding: 4px 10px;
        font-size: 13px;
        font-weight: bold;
        min-width: 28px;
    }
    QPushButton:hover {
        background-color: rgba(100, 100, 100, 230);
    }
    QPushButton:pressed {
        background-color: rgba(50, 50, 50, 255);
    }
    QPushButton:checked {
        background-color: rgba(0, 120, 215, 220);
        border: 1px solid rgba(0, 150, 255, 200);
    }
"""


def _color_swatch_style():
    return """
    QPushButton {{
        background-color: {color};
        border: 2px solid rgba(255, 255, 255, 120);
        border-radius: 3px;
        min-width: 22px; max-width: 22px;
        min-height: 22px; max-height: 22px;
        padding: 0px;
    }}
    QPushButton:hover {{
        border: 2px solid white;
    }}
"""


def _inner_button_style():
    return """
    QPushButton {
        background-color: rgba(60, 60, 60, 200);
        color: white;
        border: 1px solid rgba(255, 255, 255, 60);
        border-radius: 5px;
        padding: 6px 14px;
        font-size: 13px;
        font-weight: bold;
    }
    QPushButton:hover { background-color: rgba(80, 80, 80, 220); }
    QPushButton:pressed { background-color: rgba(40, 40, 40, 255); }
"""


def _scrollbar_style():
    return """
    QScrollBar:vertical {
        background: rgba(255,255,255,15); width: 8px; border-radius: 4px;
    }
    QScrollBar::handle:vertical {
        background: rgba(255,255,255,60); border-radius: 4px; min-height: 20px;
    }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal {
        background: rgba(255,255,255,15); height: 6px; border-radius: 3px;
    }
    QScrollBar::handle:horizontal {
        background: rgba(255,255,255,60); border-radius: 3px; min-width: 20px;
    }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
"""


# Cache stylesheet strings — computed once, reused everywhere.
TOOLBAR_BUTTON_STYLE = functools.lru_cache(maxsize=1)(_toolbar_button_style)
FORMAT_BUTTON_STYLE = functools.lru_cache(maxsize=1)(_format_button_style)
COLOR_SWATCH_STYLE = functools.lru_cache(maxsize=1)(_color_swatch_style)
INNER_BUTTON_STYLE = functools.lru_cache(maxsize=1)(_inner_button_style)
SCROLLBAR_STYLE = functools.lru_cache(maxsize=1)(_scrollbar_style)


# ---------------------------------------------------------------------------
# FloatingPanel – reusable draggable / resizable panel
# ---------------------------------------------------------------------------

class FloatingPanel(QWidget):
    closed = pyqtSignal()
    minimized = pyqtSignal()

    RESIZE_MARGIN = 6
    SLIM_TITLE_HEIGHT = 8
    _PAINT_BRUSH = QColor(30, 30, 30, 220)
    _PAINT_PEN = QColor(255, 255, 255, 60)
    _EDGE_CURSORS = {
        "left": Qt.CursorShape.SizeHorCursor, "right": Qt.CursorShape.SizeHorCursor,
        "top": Qt.CursorShape.SizeVerCursor, "bottom": Qt.CursorShape.SizeVerCursor,
        "top-left": Qt.CursorShape.SizeFDiagCursor, "bottom-right": Qt.CursorShape.SizeFDiagCursor,
        "top-right": Qt.CursorShape.SizeBDiagCursor, "bottom-left": Qt.CursorShape.SizeBDiagCursor,
    }

    def __init__(self, title="Panel", parent=None):
        super().__init__(parent)
        self._title = title
        self._is_minimized = False
        self._restored_height = 400
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_rect = None
        self._resize_start_pos = None
        self._content_widget = None
        self.TITLE_BAR_HEIGHT = 32
        self._collapse_timer = QTimer(self)
        self._collapse_timer.setSingleShot(True)
        self._collapse_timer.setInterval(80)
        self._collapse_timer.timeout.connect(self._do_collapse_title_bar)
        self._setup_window()
        self._build_title_bar()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(180, self.TITLE_BAR_HEIGHT + 20)
        self.setMouseTracking(True)

    def _build_title_bar(self):
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)

        self._title_bar = QWidget(self)
        self._title_bar.setFixedHeight(self.TITLE_BAR_HEIGHT)
        self._title_bar.setStyleSheet(f"""
            background-color: rgba(20, 20, 20, 240);
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom: 1px solid {CARD_BORDER};
        """)

        tb_layout = QHBoxLayout(self._title_bar)
        tb_layout.setContentsMargins(10, 0, 4, 0)
        tb_layout.setSpacing(4)

        self._title_label = QLabel(self._title, self._title_bar)
        self._title_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        tb_layout.addWidget(self._title_label)
        tb_layout.addStretch()

        self._btn_minimize = QPushButton("▬", self._title_bar)
        self._btn_minimize.setFixedSize(26, 22)
        self._btn_minimize.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,20); color: white; border: none; border-radius: 3px; font-size: 10px; }
            QPushButton:hover { background: rgba(255,255,255,50); }
        """)
        self._btn_minimize.clicked.connect(self.toggle_minimize)
        tb_layout.addWidget(self._btn_minimize)

        self._btn_close = QPushButton("✕", self._title_bar)
        self._btn_close.setFixedSize(26, 22)
        self._btn_close.setStyleSheet("""
            QPushButton { background: rgba(220,50,50,180); color: white; border: none; border-radius: 3px; font-size: 12px; }
            QPushButton:hover { background: rgba(240,70,70,220); }
        """)
        self._btn_close.clicked.connect(self._on_close)
        tb_layout.addWidget(self._btn_close)

        self._main_layout.addWidget(self._title_bar)

        self._content_area = QWidget(self)
        self._content_area.setStyleSheet(f"background-color: {CARD_BG}; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(0)
        self._main_layout.addWidget(self._content_area)

        # Install event filter for hover title bar
        self._title_bar.installEventFilter(self)
        self._title_bar.setMouseTracking(True)
        # Start collapsed (slim)
        QTimer.singleShot(0, self._do_collapse_title_bar)

    def eventFilter(self, obj, event):
        if obj == self._title_bar and not self._is_minimized:
            if event.type() == QEvent.Type.Enter:
                self._collapse_timer.stop()
                self._expand_title_bar()
            elif event.type() == QEvent.Type.Leave:
                self._collapse_timer.start()
        return super().eventFilter(obj, event)

    def _expand_title_bar(self):
        self._title_bar.setFixedHeight(self.TITLE_BAR_HEIGHT)
        self._title_label.show()
        self._btn_minimize.show()
        self._btn_close.show()

    def _do_collapse_title_bar(self):
        if not self._is_minimized:
            self._title_bar.setFixedHeight(self.SLIM_TITLE_HEIGHT)
            self._title_label.hide()
            self._btn_minimize.hide()
            self._btn_close.hide()

    def set_content_widget(self, widget):
        self._content_widget = widget
        self._content_layout.addWidget(widget)

    def set_title(self, title):
        self._title = title
        self._title_label.setText(title)

    def toggle_minimize(self):
        if self._is_minimized:
            # Restore
            self._content_area.show()
            self.setFixedHeight(16777215)
            self.resize(self.width(), self._restored_height)
            self._is_minimized = False
            self._btn_minimize.setText("▬")
            # Collapse title bar back to slim
            self._do_collapse_title_bar()
        else:
            # Minimize — show full title bar
            self._collapse_timer.stop()
            self._restored_height = self.height()
            self._content_area.hide()
            self._expand_title_bar()
            self.setFixedHeight(self.TITLE_BAR_HEIGHT)
            self._is_minimized = True
            self._btn_minimize.setText("▢")
        self.minimized.emit()

    def _on_close(self):
        self.hide()
        self.closed.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()
            edge = self._get_resize_edge(pos)
            if edge and not self._is_minimized:
                self._resize_edge = edge
                self._resize_start_rect = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
            elif pos.y() <= self._title_bar.height():
                self._drag_pos = event.globalPosition().toPoint() - self.pos()
            else:
                self._drag_pos = None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        pos = event.position().toPoint()
        if self._resize_edge and self._resize_start_pos:
            self._do_resize(event.globalPosition().toPoint())
        elif self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        else:
            edge = self._get_resize_edge(pos)
            if edge and not self._is_minimized:
                self.setCursor(self._EDGE_CURSORS.get(edge, Qt.CursorShape.ArrowCursor))
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_rect = None
        self._resize_start_pos = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def _get_resize_edge(self, pos):
        m = self.RESIZE_MARGIN
        w, h = self.width(), self.height()
        x, y = pos.x(), pos.y()
        on_left, on_right = x < m, x > w - m
        on_top, on_bottom = y < m, y > h - m
        if on_top and on_left: return "top-left"
        if on_top and on_right: return "top-right"
        if on_bottom and on_left: return "bottom-left"
        if on_bottom and on_right: return "bottom-right"
        if on_left: return "left"
        if on_right: return "right"
        if on_top: return "top"
        if on_bottom: return "bottom"
        return None

    def _do_resize(self, global_pos):
        dx = global_pos.x() - self._resize_start_pos.x()
        dy = global_pos.y() - self._resize_start_pos.y()
        r = self._resize_start_rect
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        new_rect = QRect(r)
        edge = self._resize_edge
        if "right" in edge: new_rect.setRight(max(r.right() + dx, r.left() + min_w))
        if "bottom" in edge: new_rect.setBottom(max(r.bottom() + dy, r.top() + min_h))
        if "left" in edge: new_rect.setLeft(min(r.left() + dx, r.right() - min_w))
        if "top" in edge: new_rect.setTop(min(r.top() + dy, r.bottom() - min_h))
        self.setGeometry(new_rect)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self._PAINT_BRUSH)
        painter.setPen(self._PAINT_PEN)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.end()


# ---------------------------------------------------------------------------
# OverlayToolbar – persistent top bar
# ---------------------------------------------------------------------------

class OverlayToolbar(QWidget):
    _PAINT_BRUSH = QColor(15, 15, 15, 235)
    _PAINT_PEN = QColor(255, 255, 255, 40)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._panel_buttons = {}
        self._setup_window()
        self._build_ui()

    def _setup_window(self):
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedHeight(42)
        self.setMouseTracking(True)
        self._drag_pos = None

    def _build_ui(self):
        self.setStyleSheet(f"QWidget {{ background-color: rgba(15, 15, 15, 235); border-bottom: 1px solid {CARD_BORDER}; }}")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(8, 4, 8, 4)
        outer.setSpacing(6)

        handle = QLabel("⠿", self)
        handle.setStyleSheet("color: rgba(255,255,255,60); font-size: 18px; background: transparent; border: none;")
        outer.addWidget(handle)

        # Button area — scrollable only when buttons don't fit (small screens)
        self._scroll = QScrollArea(self)
        self._scroll.setWidgetResizable(False)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setFixedHeight(34)
        self._scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }}"
            f" {SCROLLBAR_STYLE()}"
        )
        self._btn_container = QWidget()
        self._btn_container.setStyleSheet("background: transparent; border: none;")
        self._layout = QHBoxLayout(self._btn_container)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(6)
        self._layout.setSizeConstraint(QHBoxLayout.SizeConstraint.SetMinimumSize)
        self._scroll.setWidget(self._btn_container)
        # Let mouse events pass through to toolbar for dragging
        self._scroll.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._scroll.viewport().setMouseTracking(True)
        self._scroll.viewport().installEventFilter(self)
        outer.addWidget(self._scroll, 1)

        # Right-side buttons (collapse, minimize, quit) — always visible
        self._right_layout = QHBoxLayout()
        self._right_layout.setContentsMargins(0, 0, 0, 0)
        self._right_layout.setSpacing(6)
        outer.addLayout(self._right_layout)

        # Collapse button for toolbar
        self._btn_collapse = QPushButton("◀", self)
        self._btn_collapse.setStyleSheet("""
            QPushButton { background: rgba(80,80,80,200); color: white; border: 1px solid rgba(255,255,255,40);
                border-radius: 4px; font-size: 12px; padding: 2px 6px; }
            QPushButton:hover { background: rgba(100,100,100,220); }
        """)
        self._btn_collapse.setToolTip("Toolbar einklappen/ausklappen")
        self._btn_collapse.clicked.connect(self._toggle_collapse)
        self._right_layout.addWidget(self._btn_collapse)

    collapsed = pyqtSignal(bool)

    def _toggle_collapse(self):
        if self._btn_container.isVisible():
            # Hide entire toolbar — only the external RestoreButton stays
            self.hide()
            self.collapsed.emit(True)
        else:
            self._btn_container.show()
            if hasattr(self, '_btn_minimize_all'):
                self._btn_minimize_all.show()
            if hasattr(self, '_btn_quit'):
                self._btn_quit.show()
            self.show()
            self.collapsed.emit(False)

    def adjustToContent(self):
        """Resize toolbar width to fit all buttons, capped to screen width."""
        self.setMinimumWidth(0)
        self.setMaximumWidth(16777215)
        self._btn_container.adjustSize()
        # Calculate natural width: handle + buttons + right-side buttons + margins/spacing
        outer = self.layout()
        margins = outer.contentsMargins()
        spacing = outer.spacing()
        # Width of all items in the outer layout
        natural_w = margins.left() + margins.right()
        for i in range(outer.count()):
            item = outer.itemAt(i)
            if item.widget():
                if item.widget() is self._scroll:
                    # Use the button container's actual width for the scroll area
                    natural_w += self._btn_container.sizeHint().width() + 2
                else:
                    natural_w += item.widget().sizeHint().width()
            elif item.layout():
                w = 0
                for j in range(item.layout().count()):
                    sub = item.layout().itemAt(j)
                    if sub.widget():
                        w += sub.widget().sizeHint().width() + item.layout().spacing()
                natural_w += w
            if i < outer.count() - 1:
                natural_w += spacing
        screen = (self.screen() or QApplication.primaryScreen()).geometry()
        max_w = screen.width() - 40
        self.setFixedWidth(min(natural_w, max_w))

    def add_panel_button(self, panel_id, label, callback, enabled=True):
        btn = QPushButton(label, self)
        btn.setCheckable(True)
        btn.setChecked(True if enabled else False)
        btn.setEnabled(enabled)
        btn.setStyleSheet(TOOLBAR_BUTTON_STYLE())
        if enabled and callback:
            btn.clicked.connect(callback)
        if not enabled:
            btn.setToolTip("Kommt bald!")
        self._layout.addWidget(btn)
        self._panel_buttons[panel_id] = btn
        return btn

    def add_separator(self):
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,40); background: transparent; border: none;")
        sep.setFixedWidth(2)
        self._layout.addWidget(sep)

    def add_quit_button(self, callback):
        self._btn_quit = QPushButton("✕ Beenden", self)
        self._btn_quit.setStyleSheet("""
            QPushButton { background-color: rgba(180,40,40,200); color: white; border: 1px solid rgba(255,80,80,120); border-radius: 4px; padding: 5px 14px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(220,60,60,230); }
            QPushButton:pressed { background-color: rgba(150,30,30,255); }
        """)
        self._btn_quit.clicked.connect(callback)
        self._right_layout.addWidget(self._btn_quit)

    def add_minimize_button(self, callback):
        self._btn_minimize_all = QPushButton("⬇", self)
        self._btn_minimize_all.setStyleSheet("""
            QPushButton { background-color: rgba(80,80,80,200); color: white; border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 5px 10px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(100,100,100,230); }
        """)
        self._btn_minimize_all.setToolTip("Alles minimieren")
        self._btn_minimize_all.clicked.connect(callback)
        self._right_layout.addWidget(self._btn_minimize_all)
        return self._btn_minimize_all

    def add_class_selector_button(self, callback):
        btn = QPushButton("📚 Klasse", self)
        btn.setStyleSheet(TOOLBAR_BUTTON_STYLE())
        btn.clicked.connect(callback)
        self._layout.addWidget(btn)
        self._panel_buttons["class_selector"] = btn
        return btn

    def set_button_checked(self, panel_id, checked):
        btn = self._panel_buttons.get(panel_id)
        if btn:
            btn.setChecked(checked)

    def eventFilter(self, obj, event):
        """Forward mouse events from scroll viewport to enable toolbar dragging."""
        if obj is self._scroll.viewport():
            t = event.type()
            if t == event.Type.MouseButtonPress:
                self.mousePressEvent(event)
                return True
            elif t == event.Type.MouseMove:
                self.mouseMoveEvent(event)
                return True
            elif t == event.Type.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True
        return super().eventFilter(obj, event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(self._PAINT_BRUSH)
        painter.setPen(self._PAINT_PEN)
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        painter.end()


# ---------------------------------------------------------------------------
# RestoreButton – tiny button shown when everything is minimized
# ---------------------------------------------------------------------------

class RestoreButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._drag_pos = None
        self._dragged = False
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(48, 48)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._btn = QPushButton("▲", self)
        self._btn.setFixedSize(48, 48)
        self._btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 120, 215, 220);
                color: white; border: 2px solid rgba(255,255,255,100);
                border-radius: 24px; font-size: 20px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(0, 140, 235, 240); }
        """)
        self._btn.setToolTip("Overlay wiederherstellen (ziehen zum Verschieben)")
        self._btn.clicked.connect(self._on_click)
        layout.addWidget(self._btn)

    def _on_click(self):
        if not self._dragged:
            self.clicked.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
            self._dragged = False
            event.accept()

    def mouseMoveEvent(self, event):
        if self._drag_pos is not None:
            self._dragged = True
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def paintEvent(self, event):
        pass  # transparent background


# ---------------------------------------------------------------------------
# FormattingToolbar – rich text formatting (fixed height, inside scroll area)
# ---------------------------------------------------------------------------

class FormattingToolbar(QWidget):
    QUICK_COLORS = ["#FF4444", "#FF8800", "#FFDD00", "#44DD44", "#4488FF", "#AA44FF", "#FFFFFF", "#000000"]
    QUICK_HIGHLIGHTS = ["#FFFF00", "#00FF00", "#00DDFF", "#FF8800", "#FF4444", "#DD88FF", "#FFFFFF", "transparent"]

    def __init__(self, text_edit, parent=None):
        super().__init__(parent)
        self.text_edit = text_edit
        self._blink_ranges = []
        self._blink_speed = 350  # ms, default "Mittel"
        self.setFixedHeight(42)
        self._build_ui()

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.setSpacing(0)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setFixedHeight(42)
        scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")

        inner = QWidget()
        inner.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(inner)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(3)

        self.btn_bold = QPushButton("B", inner)
        self.btn_bold.setCheckable(True)
        self.btn_bold.setStyleSheet(FORMAT_BUTTON_STYLE())
        self.btn_bold.setToolTip("Fett (Strg+B)")
        self.btn_bold.clicked.connect(self._toggle_bold)
        layout.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I", inner)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setStyleSheet(FORMAT_BUTTON_STYLE())
        self.btn_italic.setToolTip("Kursiv (Strg+I)")
        self.btn_italic.clicked.connect(self._toggle_italic)
        layout.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("U", inner)
        self.btn_underline.setCheckable(True)
        self.btn_underline.setStyleSheet(FORMAT_BUTTON_STYLE())
        self.btn_underline.setToolTip("Unterstrichen (Strg+U)")
        self.btn_underline.clicked.connect(self._toggle_underline)
        layout.addWidget(self.btn_underline)

        self._add_sep(layout, inner)

        self.size_combo = QComboBox(inner)
        self.size_combo.setStyleSheet("""
            QComboBox { background-color: rgba(70,70,70,220); color: white; border: 1px solid rgba(255,255,255,80); border-radius: 5px; padding: 3px 8px; font-size: 13px; min-width: 50px; }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView { background-color: rgba(50,50,50,240); color: white; selection-background-color: rgba(0,120,215,200); }
        """)
        for size in [10, 12, 14, 16, 18, 20, 24, 28, 32, 40, 48, 56, 64, 72]:
            self.size_combo.addItem(str(size), size)
        self.size_combo.setCurrentText("14")
        self.size_combo.currentIndexChanged.connect(self._change_font_size)
        layout.addWidget(self.size_combo)

        self._add_sep(layout, inner)

        lbl_a = QLabel("A", inner)
        lbl_a.setStyleSheet("color: white; font-weight: bold; font-size: 14px; padding: 0 2px; background: transparent; border: none;")
        layout.addWidget(lbl_a)
        for color in self.QUICK_COLORS:
            btn = QPushButton("", inner)
            btn.setStyleSheet(COLOR_SWATCH_STYLE().format(color=color))
            btn.clicked.connect(lambda checked, c=color: self._set_text_color(c))
            layout.addWidget(btn)
        btn_more = QPushButton("…", inner)
        btn_more.setStyleSheet(FORMAT_BUTTON_STYLE())
        btn_more.clicked.connect(self._pick_text_color)
        layout.addWidget(btn_more)

        self._add_sep(layout, inner)

        lbl_hl = QLabel("🖍", inner)
        lbl_hl.setStyleSheet("font-size: 14px; padding: 0 2px; background: transparent; border: none;")
        layout.addWidget(lbl_hl)
        for color in self.QUICK_HIGHLIGHTS:
            btn = QPushButton("", inner)
            if color == "transparent":
                btn.setStyleSheet("QPushButton { background-color: rgba(50,50,50,200); border: 2px dashed rgba(255,255,255,120); border-radius: 3px; min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px; padding: 0px; color: white; font-size: 10px; } QPushButton:hover { border: 2px dashed white; }")
                btn.setText("✕")
            else:
                btn.setStyleSheet(COLOR_SWATCH_STYLE().format(color=color))
            btn.clicked.connect(lambda checked, c=color: self._set_highlight_color(c))
            layout.addWidget(btn)
        btn_more_hl = QPushButton("…", inner)
        btn_more_hl.setStyleSheet(FORMAT_BUTTON_STYLE())
        btn_more_hl.clicked.connect(self._pick_highlight_color)
        layout.addWidget(btn_more_hl)

        self._add_sep(layout, inner)

        # Blink feature
        self.btn_blink = QPushButton("Blinken", inner)
        self.btn_blink.setStyleSheet(FORMAT_BUTTON_STYLE())
        self.btn_blink.setToolTip("Ausgewählten Text blinken lassen")
        self.btn_blink.clicked.connect(self._toggle_blink)
        self.btn_blink.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.btn_blink.customContextMenuRequested.connect(self._show_blink_speed_menu)
        layout.addWidget(self.btn_blink)

        self.blink_duration_combo = QComboBox(inner)
        self.blink_duration_combo.setStyleSheet(
            "QComboBox { background-color: rgba(70,70,70,220); color: white; border: 1px solid rgba(255,255,255,80); "
            "border-radius: 5px; padding: 2px 6px; font-size: 12px; min-width: 40px; }"
            "QComboBox::drop-down { border: none; }"
            "QComboBox QAbstractItemView { background-color: rgba(50,50,50,240); color: white; "
            "selection-background-color: rgba(0,120,215,200); }"
        )
        self.blink_duration_combo.addItem("10s", 10)
        self.blink_duration_combo.addItem("30s", 30)
        self.blink_duration_combo.addItem("60s", 60)
        self.blink_duration_combo.addItem("\u221e", 0)
        self.blink_duration_combo.setCurrentIndex(1)
        layout.addWidget(self.blink_duration_combo)

        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

    def _add_sep(self, layout, parent):
        sep = QFrame(parent)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,40); background: transparent; border: none;")
        layout.addWidget(sep)

    def _merge_format(self, fmt):
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        cursor.mergeCharFormat(fmt)
        self.text_edit.mergeCurrentCharFormat(fmt)

    def _toggle_bold(self):
        fmt = QTextCharFormat()
        fmt.setFontWeight(QFont.Weight.Bold if self.btn_bold.isChecked() else QFont.Weight.Normal)
        self._merge_format(fmt)

    def _toggle_italic(self):
        fmt = QTextCharFormat()
        fmt.setFontItalic(self.btn_italic.isChecked())
        self._merge_format(fmt)

    def _toggle_underline(self):
        fmt = QTextCharFormat()
        fmt.setFontUnderline(self.btn_underline.isChecked())
        self._merge_format(fmt)

    def _change_font_size(self):
        size = self.size_combo.currentData()
        if size:
            fmt = QTextCharFormat()
            fmt.setFontPointSize(float(size))
            self._merge_format(fmt)

    def _set_text_color(self, c):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(c))
        self._merge_format(fmt)

    def _pick_text_color(self):
        color = QColorDialog.getColor(QColor("white"), self, "Textfarbe wählen")
        if color.isValid(): self._set_text_color(color.name())

    def _set_highlight_color(self, c):
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(0, 0, 0, 0) if c == "transparent" else QColor(c))
        self._merge_format(fmt)

    def _pick_highlight_color(self):
        color = QColorDialog.getColor(QColor("yellow"), self, "Highlight-Farbe wählen")
        if color.isValid(): self._set_highlight_color(color.name())

    def _toggle_blink(self):
        """Start blinking for selected text, or stop all blinks if nothing selected."""
        cursor = self.text_edit.textCursor()
        if not cursor.hasSelection():
            # Stop all blinks
            self.stop_all_blinks()
            return
        self._start_blink(cursor)

    def _start_blink(self, cursor):
        start = cursor.selectionStart()
        end = cursor.selectionEnd()

        # Store original foreground AND background colors for each character
        original_fg = []
        original_bg = []
        temp = QTextCursor(self.text_edit.document())
        for pos in range(start, end):
            temp.setPosition(pos)
            temp.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            fmt = temp.charFormat()
            fg = fmt.foreground().color()
            if not fg.isValid() or fg.alpha() == 0:
                fg = QColor("white")
            original_fg.append(fg)
            bg = fmt.background().color()
            original_bg.append(bg if bg.isValid() and bg.alpha() > 0 else None)

        # Keep a range cursor for auto-adjusting positions
        range_cursor = QTextCursor(self.text_edit.document())
        range_cursor.setPosition(start)
        range_cursor.setPosition(end, QTextCursor.MoveMode.KeepAnchor)

        blink_timer = QTimer(self)
        blink_timer.setInterval(self._blink_speed)

        entry = {
            "range_cursor": range_cursor,
            "original_fg": original_fg,
            "original_bg": original_bg,
            "timer": blink_timer,
            "stop_timer": None,
            "bright": True,
            "length": end - start,
        }

        def do_blink():
            entry["bright"] = not entry["bright"]
            s = entry["range_cursor"].selectionStart()
            e = entry["range_cursor"].selectionEnd()
            if e - s != entry["length"]:
                self._stop_blink_entry(entry)
                return
            tc = QTextCursor(self.text_edit.document())
            for i, pos in enumerate(range(s, e)):
                if i >= len(entry["original_fg"]):
                    break
                tc.setPosition(pos)
                tc.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
                fmt = QTextCharFormat()
                fg = QColor(entry["original_fg"][i])
                if not entry["bright"]:
                    fg.setAlpha(77)
                else:
                    fg.setAlpha(255)
                fmt.setForeground(fg)
                bg = entry["original_bg"][i]
                if bg:
                    bgc = QColor(bg)
                    if not entry["bright"]:
                        bgc.setAlpha(max(20, bgc.alpha() // 3))
                    else:
                        bgc.setAlpha(bg.alpha())
                    fmt.setBackground(bgc)
                tc.mergeCharFormat(fmt)

        blink_timer.timeout.connect(do_blink)
        blink_timer.start()

        # Duration auto-stop
        duration = self.blink_duration_combo.currentData()
        if duration and duration > 0:
            stop_timer = QTimer(self)
            stop_timer.setSingleShot(True)
            stop_timer.setInterval(duration * 1000)
            stop_timer.timeout.connect(lambda: self._stop_blink_entry(entry))
            stop_timer.start()
            entry["stop_timer"] = stop_timer

        self._blink_ranges.append(entry)

    def _stop_blink_entry(self, entry):
        entry["timer"].stop()
        if entry["stop_timer"]:
            entry["stop_timer"].stop()
        # Restore original colors (fg + bg)
        s = entry["range_cursor"].selectionStart()
        e = entry["range_cursor"].selectionEnd()
        tc = QTextCursor(self.text_edit.document())
        for i, pos in enumerate(range(s, e)):
            if i >= len(entry["original_fg"]):
                break
            tc.setPosition(pos)
            tc.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
            fmt = QTextCharFormat()
            fmt.setForeground(entry["original_fg"][i])
            bg = entry["original_bg"][i]
            if bg:
                fmt.setBackground(bg)
            tc.mergeCharFormat(fmt)
        if entry in self._blink_ranges:
            self._blink_ranges.remove(entry)

    def stop_all_blinks(self):
        for entry in self._blink_ranges[:]:
            self._stop_blink_entry(entry)
        self._blink_ranges.clear()

    def _show_blink_speed_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet(
            "QMenu { background: rgba(40,40,40,240); color: white; "
            "border: 1px solid rgba(255,255,255,60); padding: 4px; }"
            "QMenu::item { padding: 4px 16px; }"
            "QMenu::item:selected { background: rgba(0,120,215,200); }"
        )
        speeds = [("Langsam (600ms)", 600), ("Mittel (350ms)", 350), ("Schnell (150ms)", 150)]
        for label, ms in speeds:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(self._blink_speed == ms)
            action.triggered.connect(lambda checked, m=ms: self._set_blink_speed(m))
        menu.exec(self.btn_blink.mapToGlobal(pos))

    def _set_blink_speed(self, ms):
        self._blink_speed = ms


# ---------------------------------------------------------------------------
# Panel creators
# ---------------------------------------------------------------------------

def create_text_editor_panel():
    panel = FloatingPanel("📝 Texteditor")
    panel.setMinimumSize(300, 150)
    content = QWidget()
    cl = QVBoxLayout(content)
    cl.setContentsMargins(4, 4, 4, 4)
    cl.setSpacing(4)

    text_edit = QTextEdit(content)
    text_edit.setStyleSheet(f"""
        QTextEdit {{ background-color: rgba(20,20,20,200); color: white; border: 1px solid rgba(255,255,255,50); border-radius: 6px; padding: 10px; font-size: 14px; selection-background-color: rgba(0,120,215,150); }}
        {SCROLLBAR_STYLE()}
    """)
    text_edit.setPlaceholderText("Hier Text eingeben…")
    text_edit.setAcceptRichText(True)
    text_edit.setFont(QFont("Segoe UI", 14))

    toolbar = FormattingToolbar(text_edit, content)

    btn_toggle_format = QPushButton("Formatierung ▼", content)
    btn_toggle_format.setStyleSheet(INNER_BUTTON_STYLE())
    btn_toggle_format.setToolTip("Formatierungsleiste ein-/ausblenden")
    def toggle_format_toolbar():
        if toolbar.isVisible():
            toolbar.hide()
            btn_toggle_format.setText("Formatierung ▶")
        else:
            toolbar.show()
            btn_toggle_format.setText("Formatierung ▼")
    btn_toggle_format.clicked.connect(toggle_format_toolbar)

    cl.addWidget(btn_toggle_format)
    cl.addWidget(toolbar)
    cl.addWidget(text_edit)
    panel.set_content_widget(content)
    panel.text_edit = text_edit
    panel.formatting_toolbar = toolbar
    panel.closed.connect(toolbar.stop_all_blinks)

    # Keyboard shortcuts for formatting
    def toggle_bold_shortcut():
        toolbar.btn_bold.setChecked(not toolbar.btn_bold.isChecked())
        toolbar._toggle_bold()

    def toggle_italic_shortcut():
        toolbar.btn_italic.setChecked(not toolbar.btn_italic.isChecked())
        toolbar._toggle_italic()

    def toggle_underline_shortcut():
        toolbar.btn_underline.setChecked(not toolbar.btn_underline.isChecked())
        toolbar._toggle_underline()

    sc_bold = QShortcut(QKeySequence("Ctrl+B"), text_edit)
    sc_bold.setContext(Qt.ShortcutContext.WidgetShortcut)
    sc_bold.activated.connect(toggle_bold_shortcut)

    sc_italic = QShortcut(QKeySequence("Ctrl+I"), text_edit)
    sc_italic.setContext(Qt.ShortcutContext.WidgetShortcut)
    sc_italic.activated.connect(toggle_italic_shortcut)

    sc_underline = QShortcut(QKeySequence("Ctrl+U"), text_edit)
    sc_underline.setContext(Qt.ShortcutContext.WidgetShortcut)
    sc_underline.activated.connect(toggle_underline_shortcut)

    return panel


def create_student_list_panel():
    panel = FloatingPanel("📋 Schülerliste")
    panel.setMinimumSize(200, 80)
    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(8, 8, 8, 8)
    cl.setSpacing(4)

    header = QLabel("Schülerliste", content)
    header.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
    header.setAlignment(Qt.AlignmentFlag.AlignCenter)
    cl.addWidget(header)

    line = QFrame(content)
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: rgba(255,255,255,40); background: transparent; border: none;")
    cl.addWidget(line)

    scroll = QScrollArea(content)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")
    sc = QWidget()
    sc.setStyleSheet("background: transparent; border: none;")
    sl = QVBoxLayout(sc)
    sl.setContentsMargins(4, 4, 4, 4)
    sl.setSpacing(2)
    sl.addStretch()
    scroll.setWidget(sc)
    cl.addWidget(scroll)

    panel.set_content_widget(content)
    panel.header_label = header
    panel.student_layout = sl
    panel.student_container = sc
    return panel


def load_students_into_panel(panel, class_name, students, open_notes_fn=None):
    panel.header_label.setText(f"📋 Klasse {class_name}")
    panel.set_title(f"📋 Klasse {class_name}")
    layout = panel.student_layout
    while layout.count() > 1:
        item = layout.takeAt(0)
        w = item.widget()
        if w: w.deleteLater()
    for i, s in enumerate(students, 1):
        sk = f"{s.get('first_name', '')} {s.get('last_name', '')}"
        lbl = QLabel(f"  {i}. {sk}", panel.student_container)
        lbl.setStyleSheet("color: white; font-size: 14px; background: transparent; border: none; padding: 3px 6px;")
        if open_notes_fn:
            lbl.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lbl.customContextMenuRequested.connect(
                lambda pos, w=lbl, key=sk: _show_student_note_menu(w, pos, key, open_notes_fn))
        layout.insertWidget(layout.count() - 1, lbl)


def _show_student_note_menu(widget, pos, student_key, open_notes_fn):
    menu = QMenu(widget)
    menu.setStyleSheet(
        "QMenu { background: rgba(40,40,40,240); color: white; "
        "border: 1px solid rgba(255,255,255,60); padding: 4px; }"
        "QMenu::item { padding: 4px 16px; }"
        "QMenu::item:selected { background: rgba(0,120,215,200); }"
    )
    action = menu.addAction("📝 Notizen anzeigen / hinzufügen")
    action.triggered.connect(lambda: open_notes_fn(student_key))
    menu.exec(widget.mapToGlobal(pos))


# ---------------------------------------------------------------------------
# Class Editor Panel (Create / Edit)
# ---------------------------------------------------------------------------

class StudentEntryRow(QWidget):
    """A row with Vorname + Nachname fields and a remove button."""

    def __init__(self, on_enter_nachname, on_remove, first_name="", last_name="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(6)

        field_style = (
            "QLineEdit { background: rgba(50,50,50,200); color: white; "
            "border: 1px solid rgba(255,255,255,60); border-radius: 4px; "
            "padding: 5px; font-size: 13px; }"
        )

        self.vorname = QLineEdit(self)
        self.vorname.setPlaceholderText("Vorname")
        self.vorname.setText(first_name)
        self.vorname.setStyleSheet(field_style)
        layout.addWidget(self.vorname)

        self.nachname = QLineEdit(self)
        self.nachname.setPlaceholderText("Nachname")
        self.nachname.setText(last_name)
        self.nachname.setStyleSheet(field_style)
        layout.addWidget(self.nachname)

        btn_remove = QPushButton("✕", self)
        btn_remove.setFixedSize(28, 28)
        btn_remove.setStyleSheet(
            "QPushButton { color: #FF4444; background: rgba(255,255,255,10); "
            "border: 1px solid rgba(255,255,255,30); border-radius: 14px; font-size: 14px; }"
            "QPushButton:hover { background: rgba(220,50,50,100); }"
        )
        btn_remove.clicked.connect(on_remove)
        layout.addWidget(btn_remove)

        # Enter in Vorname -> jump to Nachname
        self.vorname.returnPressed.connect(lambda: self.nachname.setFocus())
        # Enter in Nachname -> add new row
        self.nachname.returnPressed.connect(on_enter_nachname)


def create_class_editor_panel(on_save_callback, class_name="", students=None, edit_filepath=None):
    """Create a panel for adding/editing a class."""
    panel = FloatingPanel("📚 Klasse erstellen" if not edit_filepath else "📚 Klasse bearbeiten")
    panel.setMinimumSize(380, 400)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # Class name field
    name_row = QHBoxLayout()
    name_lbl = QLabel("Klassenname:", content)
    name_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent; border: none;")
    name_edit = QLineEdit(content)
    name_edit.setPlaceholderText("z.B. 8b")
    name_edit.setText(class_name)
    name_edit.setStyleSheet(
        "QLineEdit { background: rgba(50,50,50,200); color: white; "
        "border: 1px solid rgba(255,255,255,60); border-radius: 4px; "
        "padding: 6px; font-size: 14px; }"
    )
    name_row.addWidget(name_lbl)
    name_row.addWidget(name_edit)
    cl.addLayout(name_row)

    # Scrollable student entries
    scroll = QScrollArea(content)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")
    scroll_widget = QWidget()
    scroll_widget.setStyleSheet("background: transparent; border: none;")
    scroll_layout = QVBoxLayout(scroll_widget)
    scroll_layout.setContentsMargins(0, 0, 0, 0)
    scroll_layout.setSpacing(4)
    scroll_layout.addStretch()
    scroll.setWidget(scroll_widget)
    cl.addWidget(scroll)

    rows = []

    def add_row(first_name="", last_name="", focus_first=False):
        def on_enter():
            add_row(focus_first=True)

        container = [None]  # will hold the row reference

        def on_remove():
            row_widget = container[0]
            if row_widget and row_widget in rows:
                rows.remove(row_widget)
                row_widget.deleteLater()

        row = StudentEntryRow(on_enter, on_remove, first_name, last_name, scroll_widget)
        container[0] = row
        rows.append(row)
        scroll_layout.insertWidget(scroll_layout.count() - 1, row)
        if focus_first:
            row.vorname.setFocus()
        return row

    # Pre-fill existing students or add one empty row
    if students:
        for s in students:
            add_row(s.get("first_name", ""), s.get("last_name", ""))
    else:
        add_row(focus_first=True)

    # Add student button
    btn_add = QPushButton("➕ Schüler hinzufügen", content)
    btn_add.setStyleSheet(INNER_BUTTON_STYLE())
    btn_add.clicked.connect(lambda: add_row(focus_first=True))
    cl.addWidget(btn_add)

    # Save button
    btn_save = QPushButton("💾 Klasse speichern", content)
    btn_save.setStyleSheet(INNER_BUTTON_STYLE())
    cl.addWidget(btn_save)

    # Status label
    status_lbl = QLabel("", content)
    status_lbl.setStyleSheet("color: #FFDD00; font-size: 12px; background: transparent; border: none;")
    cl.addWidget(status_lbl)

    panel.set_content_widget(content)

    def save_class():
        cn = name_edit.text().strip()
        if not cn:
            status_lbl.setText("⚠ Bitte Klassennamen eingeben!")
            status_lbl.setStyleSheet("color: #FF4444; font-size: 12px; background: transparent; border: none;")
            return

        student_list = []
        for row in rows:
            fn = row.vorname.text().strip()
            ln = row.nachname.text().strip()
            if fn or ln:
                student_list.append({"first_name": fn, "last_name": ln})

        if not student_list:
            status_lbl.setText("⚠ Bitte mindestens einen Schüler eingeben!")
            status_lbl.setStyleSheet("color: #FF4444; font-size: 12px; background: transparent; border: none;")
            return

        data = {"class_name": cn, "students": student_list}

        if edit_filepath:
            filepath = edit_filepath
        else:
            safe_name = "".join(c if c.isalnum() else "_" for c in cn)
            filepath = os.path.join(get_classes_dir(), f"class_{safe_name}.json")

        try:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            status_lbl.setText(f"✅ Klasse '{cn}' gespeichert!")
            status_lbl.setStyleSheet("color: #44DD44; font-size: 12px; background: transparent; border: none;")
            if on_save_callback:
                on_save_callback(filepath)
            panel.close()
        except Exception as e:
            status_lbl.setText(f"⚠ Fehler: {e}")
            status_lbl.setStyleSheet("color: #FF4444; font-size: 12px; background: transparent; border: none;")

    btn_save.clicked.connect(save_class)

    return panel


# ---------------------------------------------------------------------------
# Timer / Stopwatch Panel
# ---------------------------------------------------------------------------

class CountdownClockWidget(QWidget):
    """Circular pie-chart countdown clock drawn with QPainter."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0  # 1.0 = full, 0.0 = empty
        self._color = self._COLOR_GREEN
        self.setMinimumSize(60, 60)

    _COLOR_GREEN = QColor(0, 180, 80)
    _COLOR_YELLOW = QColor(255, 200, 0)
    _COLOR_RED = QColor(220, 50, 50)
    _BG_PEN = QPen(QColor(255, 255, 255, 40), 2)
    _BG_BRUSH = QBrush(QColor(40, 40, 40, 180))

    def set_progress(self, fraction):
        self._progress = max(0.0, min(1.0, fraction))
        if self._progress > 0.5:
            self._color = self._COLOR_GREEN
        elif self._progress > 0.25:
            self._color = self._COLOR_YELLOW
        else:
            self._color = self._COLOR_RED
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 4
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        rect = QRect(x, y, side, side)
        painter.setPen(self._BG_PEN)
        painter.setBrush(self._BG_BRUSH)
        painter.drawEllipse(rect)
        if self._progress > 0.001:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._color))
            span = int(self._progress * 360 * 16)
            painter.drawPie(rect.adjusted(3, 3, -3, -3), 90 * 16, span)
        painter.end()


class MiniCountdownClock(QWidget):
    """Tiny pie-chart countdown clock for traffic light counters.
    Colors reversed from timer: starts red, transitions yellow, then green."""
    _COLOR_RED = QColor(220, 50, 50)
    _COLOR_YELLOW = QColor(255, 200, 0)
    _COLOR_GREEN = QColor(0, 180, 80)
    _BG_PEN = QPen(QColor(255, 255, 255, 40), 1)
    _BG_BRUSH = QBrush(QColor(40, 40, 40, 180))

    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self._color = self._COLOR_RED

    def set_progress(self, fraction):
        clamped = max(0.0, min(1.0, fraction))
        # Skip repaint if progress change is < 1% (invisible at small widget sizes)
        if abs(clamped - self._progress) < 0.01:
            return
        self._progress = clamped
        if self._progress > 0.5:
            self._color = self._COLOR_RED
        elif self._progress > 0.25:
            self._color = self._COLOR_YELLOW
        else:
            self._color = self._COLOR_GREEN
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        side = min(self.width(), self.height()) - 2
        x = (self.width() - side) // 2
        y = (self.height() - side) // 2
        rect = QRect(x, y, side, side)
        painter.setPen(self._BG_PEN)
        painter.setBrush(self._BG_BRUSH)
        painter.drawEllipse(rect)
        if self._progress > 0.001:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(self._color))
            span = int(self._progress * 360 * 16)
            painter.drawPie(rect.adjusted(1, 1, -1, -1), 90 * 16, span)
        painter.end()


def create_timer_panel():
    panel = FloatingPanel("⏱ Timer / Stoppuhr")
    panel.setMinimumSize(260, 250)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # Mode toggle
    mode_row = QHBoxLayout()
    btn_timer = QPushButton("Timer", content)
    btn_timer.setCheckable(True)
    btn_timer.setChecked(True)
    btn_timer.setStyleSheet(FORMAT_BUTTON_STYLE())
    btn_stopwatch = QPushButton("Stoppuhr", content)
    btn_stopwatch.setCheckable(True)
    btn_stopwatch.setStyleSheet(FORMAT_BUTTON_STYLE())
    mode_row.addWidget(btn_timer)
    mode_row.addWidget(btn_stopwatch)
    mode_row.addStretch()
    cl.addLayout(mode_row)

    # Circular countdown clock
    clock_widget = CountdownClockWidget(content)
    clock_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    cl.addWidget(clock_widget, 1)

    # +/- digit adjustment buttons + display
    # Layout: row of +buttons, row of digit labels, row of -buttons
    def make_pm_btn_style(fsz=14, min_w=24, min_h=20):
        return (
            f"QPushButton {{ color: white; font-size: {fsz}px; font-weight: bold; "
            f"background: rgba(60,60,60,200); border: 1px solid rgba(255,255,255,40); "
            f"border-radius: 4px; padding: 2px; min-width: {min_w}px; min-height: {min_h}px; }}"
            f"QPushButton:hover {{ background: rgba(100,100,100,220); }}"
        )
    digit_container = QWidget(content)
    digit_container.setStyleSheet("background: transparent; border: none;")
    digit_vbox = QVBoxLayout(digit_container)
    digit_vbox.setContentsMargins(0, 0, 0, 0)
    digit_vbox.setSpacing(0)

    # + buttons row
    plus_row = QHBoxLayout()
    plus_row.setSpacing(2)
    plus_row.addStretch()
    plus_btns = []
    pm_spacers = []
    for _ in range(4):  # min10, min1, sec10, sec1
        b = QPushButton("+", content)
        b.setStyleSheet(make_pm_btn_style())
        plus_btns.append(b)
        plus_row.addWidget(b)
        if _ == 1:  # spacer for ":"
            spacer_lbl = QLabel("", content)
            spacer_lbl.setFixedWidth(12)
            spacer_lbl.setStyleSheet("background: transparent; border: none;")
            plus_row.addWidget(spacer_lbl)
            pm_spacers.append(spacer_lbl)
    plus_row.addStretch()
    digit_vbox.addLayout(plus_row)

    # Display row (digits)
    timer_font_state = {"color": "white"}

    def get_timer_font_size():
        return max(20, min(120, content.width() // 6))

    display = QLabel("05:00", content)
    display.setAlignment(Qt.AlignmentFlag.AlignCenter)

    _cached_display = [None, None, None]  # [color, size, result]

    def make_display_style(color=None):
        if color:
            timer_font_state["color"] = color
        c = timer_font_state["color"]
        sz = get_timer_font_size()
        if _cached_display[0] == c and _cached_display[1] == sz:
            return _cached_display[2]
        result = f"color: {c}; font-size: {sz}px; font-weight: bold; font-family: 'Consolas', monospace; background: transparent; border: none;"
        _cached_display[:] = [c, sz, result]
        return result

    display.setStyleSheet(make_display_style())
    digit_vbox.addWidget(display)

    # - buttons row
    minus_row = QHBoxLayout()
    minus_row.setSpacing(2)
    minus_row.addStretch()
    minus_btns = []
    for _ in range(4):
        b = QPushButton("-", content)
        b.setStyleSheet(make_pm_btn_style())
        minus_btns.append(b)
        minus_row.addWidget(b)
        if _ == 1:  # spacer for ":"
            spacer_lbl2 = QLabel("", content)
            spacer_lbl2.setFixedWidth(12)
            spacer_lbl2.setStyleSheet("background: transparent; border: none;")
            minus_row.addWidget(spacer_lbl2)
            pm_spacers.append(spacer_lbl2)
    minus_row.addStretch()
    digit_vbox.addLayout(minus_row)

    cl.addWidget(digit_container)

    # Timer input row (hidden initial values)
    input_row = QHBoxLayout()
    lbl_min = QLabel("Min:", content)
    lbl_min.setStyleSheet("color: white; background: transparent; border: none;")
    spin_min = QSpinBox(content)
    spin_min.setRange(0, 99)
    spin_min.setValue(5)
    spin_min.setStyleSheet("QSpinBox { background: rgba(50,50,50,200); color: white; border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 4px; }")
    lbl_sec = QLabel("Sek:", content)
    lbl_sec.setStyleSheet("color: white; background: transparent; border: none;")
    spin_sec = QSpinBox(content)
    spin_sec.setRange(0, 59)
    spin_sec.setValue(0)
    spin_sec.setStyleSheet(spin_min.styleSheet())
    timer_input_labels = [lbl_min, lbl_sec]
    timer_spinboxes = [spin_min, spin_sec]
    input_row.addWidget(lbl_min)
    input_row.addWidget(spin_min)
    input_row.addWidget(lbl_sec)
    input_row.addWidget(spin_sec)
    input_row.addStretch()
    input_widget = QWidget(content)
    input_widget.setLayout(input_row)

    # Settings collapsible container
    settings_container = QWidget(content)
    settings_container.setStyleSheet("background: transparent; border: none;")
    settings_layout = QVBoxLayout(settings_container)
    settings_layout.setContentsMargins(0, 0, 0, 0)
    settings_layout.setSpacing(4)
    settings_layout.addWidget(input_widget)

    # Sound selector
    sound_row = QHBoxLayout()
    sound_lbl = QLabel("Ton:", content)
    sound_lbl.setStyleSheet("color: white; background: transparent; border: none;")
    sound_combo = QComboBox(content)
    sound_combo.setStyleSheet(
        "QComboBox { background-color: rgba(70,70,70,220); color: white; border: 1px solid rgba(255,255,255,80); "
        "border-radius: 5px; padding: 3px 8px; font-size: 13px; min-width: 120px; }"
        "QComboBox::drop-down { border: none; }"
        "QComboBox QAbstractItemView { background-color: rgba(50,50,50,240); color: white; "
        "selection-background-color: rgba(0,120,215,200); }"
    )
    sounds_dir = get_sounds_dir()
    sound_files = sorted(glob.glob(os.path.join(sounds_dir, "*.wav")))
    if not sound_files:
        sound_combo.addItem("(kein Ton)", "")
    for sf in sound_files:
        sound_combo.addItem(os.path.basename(sf), sf)
    sound_row.addWidget(sound_lbl)
    sound_row.addWidget(sound_combo)
    sound_row.addStretch()
    settings_layout.addLayout(sound_row)

    # Create sound effect object
    alarm_sound = None
    if HAS_MULTIMEDIA:
        alarm_sound = QSoundEffect()
        if sound_combo.currentData():
            alarm_sound.setSource(QUrl.fromLocalFile(sound_combo.currentData()))
        alarm_sound.setLoopCount(1)
        alarm_sound.setVolume(1.0)
        def update_alarm_sound(index):
            path = sound_combo.itemData(index)
            if path:
                alarm_sound.setSource(QUrl.fromLocalFile(path))
        sound_combo.currentIndexChanged.connect(update_alarm_sound)

    btn_toggle_settings = QPushButton("Einstellungen ▼", content)
    btn_toggle_settings.setStyleSheet(INNER_BUTTON_STYLE())
    def toggle_settings():
        if settings_container.isVisible():
            settings_container.hide()
            btn_toggle_settings.setText("Einstellungen ▶")
        else:
            settings_container.show()
            btn_toggle_settings.setText("Einstellungen ▼")
    btn_toggle_settings.clicked.connect(toggle_settings)
    cl.addWidget(btn_toggle_settings)
    cl.addWidget(settings_container)

    # Buttons — Start/Pause as one toggle + Reset
    btn_row = QHBoxLayout()
    btn_start_pause = QPushButton("Start", content)
    btn_start_pause.setStyleSheet(INNER_BUTTON_STYLE())
    btn_reset = QPushButton("Reset", content)
    btn_reset.setStyleSheet(INNER_BUTTON_STYLE())
    btn_row.addWidget(btn_start_pause)
    btn_row.addWidget(btn_reset)
    cl.addLayout(btn_row)

    panel.set_content_widget(content)

    # State
    timer = QTimer()
    timer.setInterval(100)
    state = {"running": False, "mode": "timer", "ms": 0, "target_ms": 300000}

    def update_display():
        ms = state["ms"]
        total_sec = ms // 1000
        m, s = divmod(total_sec, 60)
        tenths = (ms % 1000) // 100
        if state["mode"] == "stopwatch":
            display.setText(f"{m:02d}:{s:02d}.{tenths}")
            clock_widget.set_progress(0.0)
        else:
            display.setText(f"{m:02d}:{s:02d}")
            # Update clock progress
            if state["target_ms"] > 0:
                clock_widget.set_progress(ms / state["target_ms"])
            else:
                clock_widget.set_progress(0.0)

    def tick():
        if state["mode"] == "timer":
            state["ms"] -= 100
            if state["ms"] <= 0:
                state["ms"] = 0
                timer.stop()
                state["running"] = False
                btn_start_pause.setText("Start")
                display.setStyleSheet(make_display_style("#FF4444"))
                # Play alarm sound
                if alarm_sound and sound_combo.currentData():
                    alarm_sound.play()
                elif sys.platform == "win32" and sound_combo.currentData():
                    try:
                        import winsound
                        winsound.PlaySound(sound_combo.currentData(),
                                           winsound.SND_FILENAME | winsound.SND_ASYNC)
                    except Exception:
                        pass
        else:
            state["ms"] += 100
        update_display()

    timer.timeout.connect(tick)

    def toggle_start_pause():
        if state["running"]:
            timer.stop()
            state["running"] = False
            btn_start_pause.setText("Start")
        else:
            if state["mode"] == "timer" and state["ms"] == 0:
                state["ms"] = (spin_min.value() * 60 + spin_sec.value()) * 1000
                state["target_ms"] = state["ms"]
            display.setStyleSheet(make_display_style("white"))
            state["running"] = True
            timer.start()
            btn_start_pause.setText("Pause")

    def reset():
        timer.stop()
        state["running"] = False
        btn_start_pause.setText("▶ Start")
        state["ms"] = 0 if state["mode"] == "stopwatch" else (spin_min.value() * 60 + spin_sec.value()) * 1000
        if state["mode"] == "timer":
            state["target_ms"] = state["ms"]
        display.setStyleSheet(make_display_style("white"))
        update_display()

    # +/- button handlers: adjust time on the fly
    # Positions: 0=min tens, 1=min ones, 2=sec tens, 3=sec ones
    increments = [10 * 60 * 1000, 1 * 60 * 1000, 10 * 1000, 1 * 1000]

    def adjust_time(delta_ms):
        state["ms"] = max(0, state["ms"] + delta_ms)
        state["target_ms"] = max(state["target_ms"], state["ms"])
        update_display()

    for i in range(4):
        plus_btns[i].clicked.connect(lambda checked, d=increments[i]: adjust_time(d))
        minus_btns[i].clicked.connect(lambda checked, d=increments[i]: adjust_time(-d))

    def set_timer_mode():
        btn_timer.setChecked(True)
        btn_stopwatch.setChecked(False)
        state["mode"] = "timer"
        input_widget.show()
        for b in plus_btns:
            b.show()
        for b in minus_btns:
            b.show()
        for s in pm_spacers:
            s.show()
        clock_widget.show()
        reset()

    def set_stopwatch_mode():
        btn_timer.setChecked(False)
        btn_stopwatch.setChecked(True)
        state["mode"] = "stopwatch"
        input_widget.hide()
        for b in plus_btns:
            b.hide()
        for b in minus_btns:
            b.hide()
        for s in pm_spacers:
            s.hide()
        clock_widget.hide()
        reset()

    btn_start_pause.clicked.connect(toggle_start_pause)
    btn_reset.clicked.connect(reset)
    btn_timer.clicked.connect(set_timer_mode)
    btn_stopwatch.clicked.connect(set_stopwatch_mode)

    # Resize handler — scale ALL elements (debounced 60ms)
    timer_action_btns = [btn_start_pause, btn_reset]
    timer_mode_btns = [btn_timer, btn_stopwatch]
    orig_resize = content.resizeEvent
    _timer_resize_pending = QTimer()
    _timer_resize_pending.setSingleShot(True)
    _timer_resize_pending.setInterval(60)
    _last_timer_scale = [0]

    def _do_timer_resize():
        w = content.width()
        h = content.height()
        scale = min(w, h)
        if scale == _last_timer_scale[0]:
            return
        _last_timer_scale[0] = scale

        display.setStyleSheet(make_display_style())

        pm_fsz = max(10, scale // 20)
        pm_w = max(20, scale // 14)
        pm_h = max(16, scale // 18)
        pm_style = make_pm_btn_style(pm_fsz, pm_w, pm_h)
        for b in plus_btns + minus_btns:
            b.setStyleSheet(pm_style)
        spacer_w = max(8, scale // 30)
        for s in pm_spacers:
            s.setFixedWidth(spacer_w)

        mode_fsz = max(10, scale // 28)
        mode_pad_h = max(2, scale // 100)
        mode_pad_w = max(6, scale // 40)
        mode_style = (
            f"QPushButton {{ background-color: rgba(70,70,70,220); color: white; "
            f"border: 1px solid rgba(255,255,255,80); border-radius: 5px; "
            f"padding: {mode_pad_h}px {mode_pad_w}px; font-size: {mode_fsz}px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: rgba(100,100,100,230); }}"
            f"QPushButton:pressed {{ background-color: rgba(50,50,50,255); }}"
            f"QPushButton:checked {{ background-color: rgba(0,120,215,200); border: 2px solid rgba(0,150,255,220); }}"
        )
        for b in timer_mode_btns:
            b.setStyleSheet(mode_style)

        action_fsz = max(10, scale // 25)
        action_pad_h = max(4, scale // 80)
        action_pad_w = max(8, scale // 35)
        action_style = (
            f"QPushButton {{ background-color: rgba(60,60,60,200); color: white; "
            f"border: 1px solid rgba(255,255,255,60); border-radius: 5px; "
            f"padding: {action_pad_h}px {action_pad_w}px; font-size: {action_fsz}px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: rgba(80,80,80,220); }}"
            f"QPushButton:pressed {{ background-color: rgba(50,50,50,255); }}"
        )
        for b in timer_action_btns:
            b.setStyleSheet(action_style)

        input_fsz = max(10, scale // 28)
        for lbl in timer_input_labels:
            font = lbl.font()
            font.setPointSize(input_fsz)
            lbl.setFont(font)
        spin_style = (
            f"QSpinBox {{ background: rgba(50,50,50,200); color: white; "
            f"border: 1px solid rgba(255,255,255,60); border-radius: 4px; "
            f"padding: 4px; font-size: {input_fsz}px; }}"
        )
        for sb in timer_spinboxes:
            sb.setStyleSheet(spin_style)

    _timer_resize_pending.timeout.connect(_do_timer_resize)

    def on_timer_resize(event):
        if orig_resize:
            orig_resize(event)
        _timer_resize_pending.start()

    content.resizeEvent = on_timer_resize

    update_display()
    panel._timer_qobj = timer
    panel._timer_state = state
    return panel


# ---------------------------------------------------------------------------
# Random Name Picker + Group Maker Panel
# ---------------------------------------------------------------------------

def create_random_panel(get_students_fn):
    """get_students_fn: callable returning (class_name, [students]) or None."""
    panel = FloatingPanel("🎲 Zufall / Gruppen")
    panel.setMinimumSize(280, 200)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # Random name section
    lbl_section1 = QLabel("🎲 Zufälliger Name", content)
    lbl_section1.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
    cl.addWidget(lbl_section1)

    name_display = QLabel("—", content)
    name_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
    name_display.setStyleSheet("color: #FFDD00; font-size: 28px; font-weight: bold; background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); border-radius: 8px; padding: 16px; min-height: 40px;")
    cl.addWidget(name_display)

    pick_row = QHBoxLayout()
    btn_pick = QPushButton("🎲 Name ziehen", content)
    btn_pick.setStyleSheet(INNER_BUTTON_STYLE())
    pick_row.addWidget(btn_pick)
    pick_row.addStretch()
    cl.addLayout(pick_row)

    # Separator
    sep = QFrame(content)
    sep.setFrameShape(QFrame.Shape.HLine)
    sep.setStyleSheet("color: rgba(255,255,255,40); background: transparent; border: none;")
    cl.addWidget(sep)

    # Group maker section
    lbl_section2 = QLabel("👥 Gruppen erstellen", content)
    lbl_section2.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
    cl.addWidget(lbl_section2)

    group_input_row = QHBoxLayout()
    lbl_groups = QLabel("Anzahl Gruppen:", content)
    lbl_groups.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    spin_groups = QSpinBox(content)
    spin_groups.setRange(2, 10)
    spin_groups.setValue(3)
    spin_groups.setStyleSheet("QSpinBox { background: rgba(50,50,50,200); color: white; border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 4px; font-size: 14px; min-width: 50px; }")
    btn_shuffle = QPushButton("🔀 Mischen!", content)
    btn_shuffle.setStyleSheet(INNER_BUTTON_STYLE())
    group_input_row.addWidget(lbl_groups)
    group_input_row.addWidget(spin_groups)
    group_input_row.addWidget(btn_shuffle)
    group_input_row.addStretch()
    cl.addLayout(group_input_row)

    # Group results scroll area
    group_scroll = QScrollArea(content)
    group_scroll.setWidgetResizable(True)
    group_scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")
    group_container = QWidget()
    group_container.setStyleSheet("background: transparent; border: none;")
    group_layout = QVBoxLayout(group_container)
    group_layout.setContentsMargins(4, 4, 4, 4)
    group_layout.setSpacing(4)
    group_layout.addStretch()
    group_scroll.setWidget(group_container)
    cl.addWidget(group_scroll)

    panel.set_content_widget(content)

    picked = []

    def pick_name():
        result = get_students_fn()
        if not result:
            name_display.setText("⚠ Keine Klasse geladen")
            return
        _, students = result
        available = [s for s in students if s not in picked]
        if not available:
            picked.clear()
            available = students[:]
        if available:
            s = random.choice(available)
            picked.append(s)
            name_display.setText(f"{s.get('first_name','')} {s.get('last_name','')}")

    def shuffle_groups():
        result = get_students_fn()
        if not result:
            return
        _, students = result
        n = spin_groups.value()
        shuffled = students[:]
        random.shuffle(shuffled)
        groups = [[] for _ in range(n)]
        for i, s in enumerate(shuffled):
            groups[i % n].append(s)

        # Clear old
        while group_layout.count() > 1:
            item = group_layout.takeAt(0)
            w = item.widget()
            if w: w.deleteLater()

        for gi, g in enumerate(groups, 1):
            header = QLabel(f"Gruppe {gi}:", group_container)
            header.setStyleSheet("color: #4488FF; font-size: 14px; font-weight: bold; background: transparent; border: none;")
            group_layout.insertWidget(group_layout.count() - 1, header)
            for s in g:
                lbl = QLabel(f"  • {s.get('first_name','')} {s.get('last_name','')}", group_container)
                lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none; padding: 1px 8px;")
                group_layout.insertWidget(group_layout.count() - 1, lbl)

    btn_pick.clicked.connect(pick_name)
    btn_shuffle.clicked.connect(shuffle_groups)
    return panel


# ---------------------------------------------------------------------------
# Traffic Light Panel (two modes) – with drag & drop in sort mode
# ---------------------------------------------------------------------------

LIGHT_COLORS = {"green": "#44DD44", "yellow": "#FFDD00", "red": "#FF4444"}
LIGHT_ORDER = ["green", "yellow", "red"]
LIGHT_EMOJI = {"green": "🟢", "yellow": "🟡", "red": "🔴"}
LIGHT_NAMES_DE = {"green": "Grün", "yellow": "Gelb", "red": "Rot"}


class MiniClockWidget(QWidget):
    """Standalone mini pie-chart countdown clock for click mode."""
    _BG_PEN = QPen(QColor(255, 255, 255, 40), 1)
    _BG_BRUSH = QBrush(QColor(40, 40, 40, 180))
    _COLOR_RED = QColor(220, 50, 50)
    _COLOR_YELLOW = QColor(255, 200, 0)
    _COLOR_GREEN = QColor(0, 180, 80)

    def __init__(self, size=16, parent=None):
        super().__init__(parent)
        self._progress = 1.0
        self._color = self._COLOR_RED
        self.setFixedSize(size, size)
        self.hide()

    def set_progress(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        self._progress = fraction
        if fraction > 0.5:
            self._color = self._COLOR_RED
        elif fraction > 0.25:
            self._color = self._COLOR_YELLOW
        else:
            self._color = self._COLOR_GREEN
        self.update()

    def set_size(self, size):
        self.setFixedSize(size, size)

    def paintEvent(self, event):
        if self._progress < 0.001:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        p.setPen(self._BG_PEN)
        p.setBrush(self._BG_BRUSH)
        p.drawEllipse(r)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(self._color))
        span = int(self._progress * 360 * 16)
        p.drawPie(r.adjusted(1, 1, -1, -1), 90 * 16, span)
        p.end()



class _ClockHandle:
    """Proxy for controlling the mini clock painted inside a DraggableStudentLabel.
    Provides the same interface as MiniCountdownClock (set_progress/show/hide)."""
    __slots__ = ('_label',)
    _COLOR_RED = QColor(220, 50, 50)
    _COLOR_YELLOW = QColor(255, 200, 0)
    _COLOR_GREEN = QColor(0, 180, 80)

    def __init__(self, label):
        self._label = label

    def set_progress(self, fraction):
        fraction = max(0.0, min(1.0, fraction))
        self._label._clock_progress = fraction
        if fraction > 0.5:
            self._label._clock_color = self._COLOR_RED
        elif fraction > 0.25:
            self._label._clock_color = self._COLOR_YELLOW
        else:
            self._label._clock_color = self._COLOR_GREEN
        self._label.update()

    def show(self):
        if self._label._clock_progress < 0:
            self._label._clock_progress = 1.0
        self._label.update()

    def hide(self):
        self._label._clock_progress = -1.0
        self._label.update()


class DraggableStudentLabel(QWidget):
    """A draggable+clickable student widget for sort mode.
    Paints name text and optional mini countdown clock directly — no child widgets
    that could intercept mouse events."""

    _BG_BRUSH = QBrush(QColor(255, 255, 255, 10))
    _BG_PEN = QPen(QColor(255, 255, 255, 20), 1)
    _TEXT_PEN = QColor(255, 255, 255)
    _CLOCK_BG_PEN = QPen(QColor(255, 255, 255, 40), 1)
    _CLOCK_BG_BRUSH = QBrush(QColor(40, 40, 40, 180))

    def __init__(self, student_key, color, state, refresh_fn, click_callback=None, parent=None):
        super().__init__(parent)
        self._student_key = student_key
        self._color = color
        self._state = state
        self._refresh_fn = refresh_fn
        self._click_callback = click_callback
        self._drag_started = False
        self._font = QWidget.font(self)
        self._notes_getter = None  # fn(student_key) -> list of active notes
        self._hover_timer = QTimer(self)
        self._hover_timer.setSingleShot(True)
        self._hover_timer.setInterval(3000)
        self._hover_timer.timeout.connect(self._show_notes_tooltip)
        self.setMouseTracking(True)

        # Clock state (painted inline, no child widget)
        self._clock_progress = -1.0  # < 0 means hidden
        self._clock_color = QColor(220, 50, 50)

        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)

        # Build display text with counter
        count = state.get("counters", {}).get(student_key, 0)
        self._display_text = f"  {student_key}"
        if state.get("counter_enabled") and count > 0:
            self._display_text += f" x{count}"

        # Register clock handle for countdown updates
        has_countdown = state.get("countdown_active", {}).get(student_key)
        if state.get("counter_enabled") or has_countdown:
            handle = _ClockHandle(self)
            state.setdefault("clock_widgets", {})[student_key] = handle
            if has_countdown:
                total = state.get("countdown_total", {}).get(student_key, 1)
                remaining = state.get("countdowns", {}).get(student_key, 0)
                if total > 0:
                    handle.set_progress(remaining / total)

    def setFont(self, font):
        self._font = QFont(font)
        self.update()
        self.updateGeometry()

    def font(self):
        return self._font

    def fontMetrics(self):
        return QFontMetrics(self._font)

    def text(self):
        return self._display_text

    def set_display_text(self, text):
        self._display_text = text
        self.updateGeometry()
        self.update()

    def sizeHint(self):
        fm = QFontMetrics(self._font)
        text_w = fm.horizontalAdvance(self._display_text)
        clock_w = fm.height() + 8 if self._clock_progress >= 0 else 0
        return QSize(text_w + clock_w + 16, fm.height() + 8)

    def minimumSizeHint(self):
        return self.sizeHint()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # Background
        p.setPen(self._BG_PEN)
        p.setBrush(self._BG_BRUSH)
        p.drawRoundedRect(self.rect().adjusted(0, 0, -1, -1), 4, 4)
        # Text
        p.setFont(self._font)
        p.setPen(self._TEXT_PEN)
        fm = QFontMetrics(self._font)
        text_rect = self.rect().adjusted(4, 2, -4, -2)
        if self._clock_progress >= 0:
            text_rect.setRight(text_rect.right() - fm.height() - 8)
        p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, self._display_text)
        # Mini countdown clock
        if self._clock_progress >= 0 and self._clock_progress > 0.001:
            ch = fm.height()
            cx = self.width() - ch - 6
            cy = (self.height() - ch) // 2
            clock_rect = QRect(cx, cy, ch, ch)
            p.setPen(self._CLOCK_BG_PEN)
            p.setBrush(self._CLOCK_BG_BRUSH)
            p.drawEllipse(clock_rect)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(self._clock_color))
            span = int(self._clock_progress * 360 * 16)
            p.drawPie(clock_rect.adjusted(1, 1, -1, -1), 90 * 16, span)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._start_pos = event.globalPosition().toPoint()
            self._drag_started = False
        event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if hasattr(self, '_start_pos'):
                diff = event.globalPosition().toPoint() - self._start_pos
                if diff.manhattanLength() > 10:
                    self._drag_started = True
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setText(self._student_key)
                    drag.setMimeData(mime)
                    pixmap = self.grab()
                    p = QPainter(pixmap)
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                    p.fillRect(pixmap.rect(), QColor(0, 0, 0, 150))
                    p.end()
                    drag.setPixmap(pixmap)
                    drag.setHotSpot(event.position().toPoint())
                    drag.exec(Qt.DropAction.MoveAction)
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
        event.accept()

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if not self._drag_started and self._click_callback:
            self._click_callback(self._student_key)
        self._drag_started = False
        event.accept()

    def set_notes_getter(self, fn):
        self._notes_getter = fn

    def enterEvent(self, event):
        self._hover_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._hover_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def _show_notes_tooltip(self):
        try:
            if not self._notes_getter:
                return
            notes = self._notes_getter(self._student_key)
            if not notes:
                return
            lines = [f"• {n['text']}  ({n.get('_remaining', '?')} UStd.)" for n in notes]
            text = "\n".join(lines)
            QToolTip.showText(self.mapToGlobal(self.rect().center()), text, self)
        except RuntimeError:
            pass  # widget already deleted


class DropZoneWidget(QWidget):
    """A drop zone for a traffic light color section with reflowing student labels."""
    def __init__(self, color_name, state, refresh_fn, click_callback=None, drop_callback=None, parent=None):
        super().__init__(parent)
        self._color_name = color_name
        self._state = state
        self._refresh_fn = refresh_fn
        self._click_callback = click_callback
        self._drop_callback = drop_callback
        self._scroll_viewport_fn = None
        self.setAcceptDrops(True)
        self.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,15); border-radius: 6px;")
        
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(4, 4, 4, 4)
        self._main_layout.setSpacing(4)

        self._header_lbl = QLabel(f"{LIGHT_EMOJI[self._color_name]} {LIGHT_NAMES_DE[self._color_name]}", self)
        self._header_lbl.setStyleSheet(
            f"color: {LIGHT_COLORS[self._color_name]}; font-weight: bold; "
            f"background: transparent; border: none; padding: 2px 4px;"
        )
        self._main_layout.addWidget(self._header_lbl)
        
        self._students_container = QWidget(self)
        self._students_layout = QGridLayout(self._students_container)
        self._students_layout.setContentsMargins(0,0,0,0)
        self._students_layout.setSpacing(4)
        self._main_layout.addWidget(self._students_container)
        self._main_layout.addStretch(1)

        self._student_lbls = []
        self._highlight = False
        rgb = QColor(LIGHT_COLORS[color_name]).getRgb()[:3]
        self._highlight_style = (
            f"background: rgba({rgb[0]},{rgb[1]},{rgb[2]}, 40); "
            f"border: 2px dashed {LIGHT_COLORS[color_name]}; border-radius: 6px;"
        )

    def set_scroll_viewport(self, fn):
        self._scroll_viewport_fn = fn

    def add_student(self, student_key):
        lbl = DraggableStudentLabel(student_key, self._color_name, self._state, self._refresh_fn,
                                    click_callback=self._click_callback, parent=self)
        notes_getter = self._state.get("_notes_getter")
        if notes_getter:
            lbl.set_notes_getter(notes_getter)
        self._student_lbls.append(lbl)
        self._state.setdefault("_label_index", {})[student_key] = lbl

    def apply_font_size(self, fsz):
        font = self._header_lbl.font()
        font.setPointSizeF(fsz + 2)
        self._header_lbl.setFont(font)
        for lbl in self._student_lbls:
            font = lbl.font()
            font.setPointSizeF(fsz)
            lbl.setFont(font)
            lbl.updateGeometry()
        self.updateGeometry()

    def reflow_students(self):
        clear_layout(self._students_layout)
        # Reset old column/row stretches from previous reflow
        for i in range(self._students_layout.columnCount()):
            self._students_layout.setColumnStretch(i, 0)
        for i in range(self._students_layout.rowCount()):
            self._students_layout.setRowStretch(i, 0)

        if not self._student_lbls: return

        # Get available width from the scroll area's viewport
        viewport_width = self.width()
        if self._scroll_viewport_fn:
            viewport_width = self._scroll_viewport_fn().width()

        # Calculate column width from font metrics of the widest name
        if self._student_lbls:
            fm = self._student_lbls[0].fontMetrics()
            max_text_w = max(fm.horizontalAdvance(lbl.text()) for lbl in self._student_lbls)
            clock_w = fm.height() + 8 if self._state.get("counter_enabled") else 0
            col_w = max(60, max_text_w + clock_w + 30)  # +30 for padding/border
        else:
            col_w = 140

        num_cols = max(1, (viewport_width - 20) // col_w)

        row, col = 0, 0
        for lbl in self._student_lbls:
            lbl.setParent(self._students_container)
            self._students_layout.addWidget(lbl, row, col)
            col += 1
            if col >= num_cols:
                col = 0
                row += 1

        for i in range(num_cols):
            self._students_layout.setColumnStretch(i, 1)
        self._students_layout.setRowStretch(row + 1, 1)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self._highlight = True
            self.setStyleSheet(self._highlight_style)

    def dragLeaveEvent(self, event):
        self._highlight = False
        self.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,15); border-radius: 6px;")

    def dropEvent(self, event):
        student_key = event.mimeData().text()
        if student_key and student_key in self._state["lights"]:
            self._state["lights"][student_key] = self._color_name
            self._highlight = False
            self.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,15); border-radius: 6px;")
            event.acceptProposedAction()
            if self._drop_callback:
                self._drop_callback(student_key, self._color_name)
            self._refresh_fn()


def create_traffic_light_panel(get_students_fn):
    panel = FloatingPanel("🚦 Ampelsystem")
    panel.setMinimumSize(200, 300)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(10, 10, 10, 10)
    cl.setSpacing(6)

    # Mode toggle (inline, like Timer)
    mode_row = QHBoxLayout()
    btn_click_mode = QPushButton("Klick", content)
    btn_click_mode.setCheckable(True)
    btn_click_mode.setChecked(True)
    btn_click_mode.setStyleSheet(FORMAT_BUTTON_STYLE())
    btn_sort_mode = QPushButton("Sortieren", content)
    btn_sort_mode.setCheckable(True)
    btn_sort_mode.setStyleSheet(FORMAT_BUTTON_STYLE())
    mode_row.addWidget(btn_click_mode)
    mode_row.addWidget(btn_sort_mode)
    mode_row.addStretch()
    cl.addLayout(mode_row)

    # --- Font size controls (will be added via insertLayout later) ---

    # Scroll area for content — scrollbars disabled, names must auto-fit
    scroll = QScrollArea(content)
    scroll.setWidgetResizable(True)
    scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")
    scroll_content = QWidget()
    scroll_content.setStyleSheet("background: transparent; border: none;")
    # Use a QGridLayout to allow reflowing names into columns
    scroll_layout = QGridLayout(scroll_content)
    scroll_layout.setContentsMargins(4, 4, 4, 4)
    scroll_layout.setSpacing(6)
    scroll.setWidget(scroll_content)
    cl.addWidget(scroll, 1) # Make the scroll area take up all extra vertical space

    # Reset button
    btn_reset = QPushButton("🟢 Alle auf Grün", content)
    btn_reset.setStyleSheet(INNER_BUTTON_STYLE())
    btn_reset.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
    btn_reset.setMaximumWidth(200)
    cl.addWidget(btn_reset, alignment=Qt.AlignmentFlag.AlignCenter)

    # Rules text areas (one per color)
    rules_header = QPushButton("Regeln ▾", content)
    rules_header.setCheckable(True)
    rules_header.setChecked(True)
    rules_header.setStyleSheet(
        "QPushButton { color: #4488FF; font-size: 13px; font-weight: bold; background: transparent; border: none; text-align: left; padding: 4px 0; }"
        "QPushButton:hover { color: #66AAFF; }"
    )
    cl.addWidget(rules_header)

    rules_container = QWidget(content)
    rules_container.setStyleSheet("background: transparent; border: none;")
    rules_grid = QGridLayout(rules_container)
    rules_grid.setContentsMargins(0, 0, 0, 0)
    rules_grid.setSpacing(6)
    rules_grid.setColumnStretch(1, 1) # Make the textbox column stretchable

    rule_style = (
        "QTextEdit {{ background: rgba(255,255,255,10); color: {color}; "
        "border: 1px solid {border}; border-radius: 6px; padding: 4px; }}"
    )

    def create_rule_row(grid, row, label_text, color, border_color, placeholder):
        label = QLabel(label_text, rules_container)
        label.setStyleSheet(f"color: {color}; font-weight: bold; background: transparent; border: none; padding-top: 4px;")
        label.setAlignment(Qt.AlignmentFlag.AlignTop)

        text_edit = QTextEdit(rules_container)
        text_edit.setPlaceholderText(placeholder)
        text_edit.setStyleSheet(rule_style.format(color="white", border=border_color))
        text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        text_edit.setMinimumWidth(60)

        def resize_text_edit():
            # Use min/max height to allow layout to adjust
            doc_height = text_edit.document().documentLayout().documentSize().height()
            margins = text_edit.contentsMargins()
            frame = text_edit.frameWidth() * 2
            h = max(30, int(doc_height + margins.top() + margins.bottom() + frame))
            text_edit.setMinimumHeight(h)
            text_edit.setMaximumHeight(h)

        text_edit.textChanged.connect(resize_text_edit)
        
        # Set a minimal initial height and resize after a delay
        text_edit.setFixedHeight(30)
        QTimer.singleShot(0, resize_text_edit)

        grid.addWidget(label, row, 0)
        grid.addWidget(text_edit, row, 1)
        return text_edit, resize_text_edit, label

    rules_green, resize_green, lbl_green = create_rule_row(rules_grid, 0, "🟢 Grün:", "#44DD44", "rgba(68,221,68,80)", "Gutes Verhalten, arbeitet mit")
    rules_yellow, resize_yellow, lbl_yellow = create_rule_row(rules_grid, 1, "🟡 Gelb:", "#FFDD00", "rgba(255,221,0,80)", "Erste Verwarnung")
    rules_red, resize_red, lbl_red = create_rule_row(rules_grid, 2, "🔴 Rot:", "#FF4444", "rgba(255,68,68,80)", "Konsequenz / Elterngespräch")
    rules_container.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    all_rule_edits = [rules_green, rules_yellow, rules_red]
    all_rule_resizers = [resize_green, resize_yellow, resize_red]
    all_rule_labels = [lbl_green, lbl_yellow, lbl_red]

    # Font size controls for rules (inside the rules container)
    font_control_style_inner = """
        QPushButton {
            background-color: rgba(70, 70, 70, 220); color: white;
            border: 1px solid rgba(255, 255, 255, 80); border-radius: 5px;
            font-size: 14px; min-width: 28px; max-width: 28px;
        }
        QPushButton:hover { background-color: rgba(100, 100, 100, 230); }
        QPushButton:pressed { background-color: rgba(50, 50, 50, 255); }
    """
    rule_font_row_inner = QHBoxLayout()
    rule_font_lbl_inner = QLabel("Schriftgröße:", rules_container)
    rule_font_lbl_inner.setStyleSheet("color: white; font-size: 12px; background: transparent; border: none;")
    btn_rule_font_down_inner = QPushButton("−", rules_container)
    btn_rule_font_up_inner = QPushButton("+", rules_container)
    btn_rule_font_down_inner.setStyleSheet(font_control_style_inner)
    btn_rule_font_up_inner.setStyleSheet(font_control_style_inner)
    rule_font_row_inner.addWidget(rule_font_lbl_inner)
    rule_font_row_inner.addStretch()
    rule_font_row_inner.addWidget(btn_rule_font_down_inner)
    rule_font_row_inner.addWidget(btn_rule_font_up_inner)
    rules_grid.addLayout(rule_font_row_inner, 3, 0, 1, 2)

    cl.addWidget(rules_container)

    def toggle_rules():
        visible = rules_header.isChecked()
        rules_container.setVisible(visible)
        rules_header.setText("Regeln ▾" if visible else "Regeln ▸")

    rules_header.clicked.connect(toggle_rules)

    panel.set_content_widget(content)

    state = {
        "students": [], "lights": {}, "mode": "click",
        "name_widgets": [], "sort_zones": {},
        "base_rule_size": 12,
        "_key_cache": {},  # student id -> key string
        # Counter system
        "counter_enabled": False,
        "counter_to_yellow": 3,
        "counter_to_red": 3,
        "counters": {},             # {student_key: int}
        # Countdown system
        "yellow_countdown_secs": 0,  # 0 = disabled
        "red_countdown_secs": 0,     # 0 = disabled
        "countdowns": {},            # {student_key: remaining_ms}
        "countdown_total": {},       # {student_key: total_ms}
        "countdown_active": {},      # {student_key: bool}
        "clock_widgets": {},         # {student_key: MiniCountdownClock}
        "_label_index": {},          # {student_key: DraggableStudentLabel} for O(1) lookup
    }

    def student_key(s):
        sid = id(s)
        cached = state["_key_cache"].get(sid)
        if cached is not None:
            return cached
        key = f"{s.get('first_name','')} {s.get('last_name','')}"
        state["_key_cache"][sid] = key
        return key

    def clear_name_widgets():
        clear_layout(scroll_layout)

        for w in state["name_widgets"]:
            widget = w[-1]
            widget.setParent(None)
            widget.hide()
            widget.deleteLater()
        state["name_widgets"] = []

        for zone in state["sort_zones"].values():
            # Detach children first to prevent dangling references
            for lbl in zone._student_lbls:
                lbl.setParent(None)
            zone._student_lbls.clear()
            zone.setParent(None)
            zone.hide()
            zone.deleteLater()
        state["sort_zones"] = {}
        state["clock_widgets"] = {}
        state["_label_index"] = {}


    _probe_font = QFont()
    _probe_font_hdr = QFont()

    def calc_name_font_size():
        """Binary-search for the largest font size (8.0-28.0 in 0.5 steps)
        where all names fit within the scroll viewport without any scrolling."""
        vp_w = max(1, scroll.viewport().width())
        vp_h = max(1, scroll.viewport().height())
        n = len(state["students"])
        if n == 0:
            return 14.0
        names = [student_key(s) for s in state["students"]]

        def fits_click(fsz_half):
            fsz = fsz_half / 2.0
            _probe_font.setPointSizeF(fsz)
            fm = QFontMetrics(_probe_font)
            row_h = fm.height() + 4
            dot_size = max(18, int(fm.height() * 1.2))
            max_name_w = max(fm.horizontalAdvance(name) for name in names)
            col_w = max(80, max_name_w + dot_size + 30)
            num_cols = max(1, (vp_w - 8) // col_w)
            num_rows = math.ceil(n / num_cols)
            total_h = 8 + num_rows * row_h + max(0, num_rows - 1) * 6
            return total_h <= vp_h

        def fits_sort(fsz_half):
            fsz = fsz_half / 2.0
            _probe_font.setPointSizeF(fsz)
            fm = QFontMetrics(_probe_font)
            _probe_font_hdr.setPointSizeF(fsz + 2)
            hdr_fm = QFontMetrics(_probe_font_hdr)
            row_h = fm.height() + 12
            header_h = hdr_fm.height() + 8
            total_h = 8
            for color in LIGHT_ORDER:
                total_h += header_h + 4
                zone_names = [student_key(s) for s in state["students"]
                              if state["lights"].get(student_key(s), "green") == color]
                if zone_names:
                    def _display_name(nm):
                        dn = f"  {nm}"
                        cnt = state.get("counters", {}).get(nm, 0)
                        if state.get("counter_enabled") and cnt > 0:
                            dn += f" x{cnt}"
                        return dn
                    max_w = max(fm.horizontalAdvance(_display_name(nm)) for nm in zone_names)
                    clock_extra = fm.height() + 8 if state.get("counter_enabled") else 0
                    col_w = max(60, max_w + clock_extra + 30)
                    nc = max(1, (vp_w - 28) // col_w)
                    nr = math.ceil(len(zone_names) / nc)
                    total_h += nr * row_h + max(0, nr - 1) * 4
                total_h += 8
            return total_h <= vp_h

        fits_fn = fits_sort if state["mode"] == "sort" else fits_click
        # Search in half-point steps: 16=8.0pt, 17=8.5pt, ..., 56=28.0pt
        lo, hi, result = 16, 56, 16
        while lo <= hi:
            mid = (lo + hi) // 2
            if fits_fn(mid):
                result = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return result / 2.0

    def apply_font_to_students(fsz):
        if state["mode"] == "click":
             for _, name_lbl, _, container in state["name_widgets"]:
                try:
                    font = name_lbl.font()
                    font.setPointSizeF(fsz)
                    name_lbl.setFont(font)
                except RuntimeError:
                    pass  # Widget already deleted
        elif state["mode"] == "sort":
            for zone in list(state["sort_zones"].values()):
                try:
                    zone.apply_font_size(fsz)
                except RuntimeError:
                    pass  # Widget already deleted

    def apply_ampel_scale():
        if not state["name_widgets"] or state["mode"] != 'click': return
        for light_btn, name_lbl, key, _ in state["name_widgets"]:
            try:
                color = state["lights"].get(key, "green")
                dot_size = int(name_lbl.fontMetrics().height() * 1.2)
                if dot_size < 18: dot_size = 18
                light_btn.setFixedSize(dot_size, dot_size)
                dot_font_size = int(dot_size * 0.8)
                light_btn.setStyleSheet(
                    f"QPushButton {{ color: {LIGHT_COLORS[color]}; font-size: {dot_font_size}px; text-align: center; background: transparent; border: none; }}"
                    f"QPushButton:hover {{ background: rgba(255,255,255,20); border-radius: {dot_size // 2}px; }}"
                )
            except RuntimeError:
                pass  # Widget already deleted

    def reflow_ampel_layout():
        clear_layout(scroll_layout)
        # Reset old column/row stretches from previous reflow
        for i in range(scroll_layout.columnCount()):
            scroll_layout.setColumnStretch(i, 0)
        for i in range(scroll_layout.rowCount()):
            scroll_layout.setRowStretch(i, 0)

        if state["mode"] == "click":
            widgets_to_flow = [w[-1] for w in state["name_widgets"]]
            if not widgets_to_flow: return

            # Estimate column width from font metrics of the widest name
            name_lbls = [w[1] for w in state["name_widgets"]]
            if name_lbls:
                fm = name_lbls[0].fontMetrics()
                max_w = max(fm.horizontalAdvance(lbl.text()) for lbl in name_lbls)
                dot_size = int(fm.height() * 1.2)
                col_w = max(80, max_w + dot_size + 30)  # name + dot + margins
            else:
                col_w = 150
            num_cols = max(1, scroll.viewport().width() // col_w)
            
            row, col = 0, 0
            for widget in widgets_to_flow:
                widget.setParent(scroll_content)
                scroll_layout.addWidget(widget, row, col)
                col += 1
                if col >= num_cols:
                    col = 0
                    row += 1
            # Add stretch to prevent items from vertically expanding and horizontally clustering
            for i in range(num_cols):
                scroll_layout.setColumnStretch(i, 1)
            scroll_layout.setRowStretch(row + 1, 1)

        elif state["mode"] == "sort":
            # In sort mode, the zones are always vertical
            for i, color in enumerate(LIGHT_ORDER):
                zone = state["sort_zones"].get(color)
                if zone:
                    try:
                        scroll_layout.addWidget(zone, i, 0)
                        zone.reflow_students()
                    except RuntimeError:
                        pass  # Widget already deleted
            scroll_layout.setRowStretch(len(LIGHT_ORDER), 1)
            scroll_layout.setColumnStretch(0, 1)


    def _update_click_btn_color(btn, color):
        """Update a click-mode dot button color without full refresh."""
        try:
            dot_size = btn.width()
            dot_font_size = int(dot_size * 0.8)
            btn.setStyleSheet(
                f"QPushButton {{ color: {LIGHT_COLORS[color]}; font-size: {dot_font_size}px; text-align: center; background: transparent; border: none; }}"
                f"QPushButton:hover {{ background: rgba(255,255,255,20); border-radius: {dot_size // 2}px; }}"
            )
        except RuntimeError:
            pass

    def _click_mode_counter(key, btn, name_lbl):
        """Handle counter click in click mode — same logic as sort mode."""
        color = state["lights"].get(key, "green")

        if color == "red":
            # Red: only reset countdown
            if state.get("countdown_active", {}).get(key):
                cd_secs = state["red_countdown_secs"]
                if cd_secs > 0:
                    state["countdowns"][key] = cd_secs * 1000
                    state["countdown_total"][key] = cd_secs * 1000
            _update_click_label(key, name_lbl)
            return

        state["counters"][key] = state["counters"].get(key, 0) + 1
        count = state["counters"][key]
        threshold = state["counter_to_yellow"] if color == "green" else state["counter_to_red"]

        if count >= threshold:
            next_color = "yellow" if color == "green" else "red"
            state["lights"][key] = next_color
            state["counters"][key] = 0
            cd_secs = state["yellow_countdown_secs"] if next_color == "yellow" else state["red_countdown_secs"]
            if cd_secs > 0:
                state["countdowns"][key] = cd_secs * 1000
                state["countdown_total"][key] = cd_secs * 1000
                state["countdown_active"][key] = True
                ensure_countdown_running()
            _update_click_btn_color(btn, next_color)
            _update_click_label(key, name_lbl)
        else:
            if state.get("countdown_active", {}).get(key):
                cd_secs = (state["yellow_countdown_secs"] if color == "yellow"
                           else state["red_countdown_secs"])
                if cd_secs > 0:
                    state["countdowns"][key] = cd_secs * 1000
                    state["countdown_total"][key] = cd_secs * 1000
            _update_click_label(key, name_lbl)

    def _update_click_label(key, name_lbl):
        """Update name label text and clock in click mode."""
        try:
            count = state.get("counters", {}).get(key, 0)
            display = key
            if state.get("counter_enabled") and count > 0:
                display += f" x{count}"
            name_lbl.setText(display)
            clock = state.get("clock_widgets", {}).get(key)
            if clock is not None:
                total = state.get("countdown_total", {}).get(key, 1)
                remaining = state.get("countdowns", {}).get(key, 0)
                if total > 0 and state.get("countdown_active", {}).get(key):
                    clock.set_progress(remaining / total)
                    clock.show()
                else:
                    clock.hide()
        except RuntimeError:
            pass

    def _show_click_note_tooltip(student_key, widget):
        try:
            ng = state.get("_notes_getter")
            if not ng:
                return
            notes = ng(student_key)
            if not notes:
                return
            lines = [f"• {n['text']}  ({n.get('_remaining', '?')} UStd.)" for n in notes]
            QToolTip.showText(widget.mapToGlobal(widget.rect().center()), "\n".join(lines), widget)
        except RuntimeError:
            pass  # widget already deleted

    def render_click_mode():
        clear_name_widgets()
        fsz = calc_name_font_size()

        for s in state["students"]:
            key = student_key(s)
            container = QWidget() # Use a simple container for the HBox
            rl = QHBoxLayout(container)
            rl.setContentsMargins(4, 2, 4, 2)
            rl.setSpacing(8)
            rl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

            light_btn = QPushButton("●", container)

            # Build display text with counter
            display = key
            count = state.get("counters", {}).get(key, 0)
            if state.get("counter_enabled") and count > 0:
                display += f" x{count}"

            # Name as clickable button (flat style, looks like a label)
            name_btn = QPushButton(display, container)
            name_btn.setStyleSheet(
                "QPushButton { color: white; background: transparent; border: none; "
                "text-align: left; padding: 0; }"
                "QPushButton:hover { color: #CCDDFF; }"
            )
            name_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            name_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            name_btn.setMouseTracking(True)
            # Hover tooltip for notes (3-second delay)
            notes_getter = state.get("_notes_getter")
            if notes_getter:
                _ht = QTimer(name_btn)
                _ht.setSingleShot(True)
                _ht.setInterval(3000)
                _ht.timeout.connect(lambda k=key, w=name_btn: _show_click_note_tooltip(k, w))
                name_btn._hover_timer = _ht
                name_btn._notes_key = key
                _orig_enter = name_btn.enterEvent
                _orig_leave = name_btn.leaveEvent
                name_btn.enterEvent = lambda ev, t=_ht, oe=_orig_enter: (t.start(), oe(ev))[-1]
                name_btn.leaveEvent = lambda ev, t=_ht, ol=_orig_leave: (t.stop(), QToolTip.hideText(), ol(ev))[-1]

            font = name_btn.font()
            font.setPointSizeF(fsz)
            name_btn.setFont(font)

            # Mini countdown clock
            clock_size = max(14, int(name_btn.fontMetrics().height() * 0.9))
            clock_w = MiniClockWidget(clock_size, container)
            if state.get("countdown_active", {}).get(key):
                total = state.get("countdown_total", {}).get(key, 1)
                remaining = state.get("countdowns", {}).get(key, 0)
                if total > 0:
                    clock_w.set_progress(remaining / total)
                    clock_w.show()
            state["clock_widgets"][key] = clock_w

            # Dot button: always cycles color manually
            def cycle(checked=False, k=key, btn=light_btn):
                cur = state["lights"].get(k, "green")
                nxt = LIGHT_ORDER[(LIGHT_ORDER.index(cur) + 1) % 3]
                state["lights"][k] = nxt
                _update_click_btn_color(btn, nxt)
                # Start/stop countdown on manual color change
                if nxt == "green":
                    state["countdown_active"][k] = False
                    state["countdowns"][k] = 0
                    state["counters"][k] = 0
                    clock_cw = state.get("clock_widgets", {}).get(k)
                    if clock_cw:
                        clock_cw.hide()
                elif nxt == "yellow":
                    cd = state.get("yellow_countdown_secs", 0)
                    if cd > 0:
                        state["countdowns"][k] = cd * 1000
                        state["countdown_total"][k] = cd * 1000
                        state["countdown_active"][k] = True
                        ensure_countdown_running()
                    state["counters"][k] = 0
                elif nxt == "red":
                    cd = state.get("red_countdown_secs", 0)
                    if cd > 0:
                        state["countdowns"][k] = cd * 1000
                        state["countdown_total"][k] = cd * 1000
                        state["countdown_active"][k] = True
                        ensure_countdown_running()
                    state["counters"][k] = 0

            # Name button: increments counter when enabled
            def on_name_click(checked=False, k=key, btn=light_btn, nlbl=name_btn):
                if state.get("counter_enabled"):
                    _click_mode_counter(k, btn, nlbl)

            light_btn.clicked.connect(cycle)
            name_btn.clicked.connect(on_name_click)
            rl.addWidget(light_btn)
            rl.addWidget(name_btn)
            rl.addWidget(clock_w)
            rl.addStretch() # Stretch inside the hbox

            state["name_widgets"].append((light_btn, name_btn, key, container))
        
    # --- Countdown timer (master timer for all student countdowns) ---
    countdown_timer = QTimer()
    countdown_timer.setInterval(1000)

    def _update_countdown_clocks():
        """Update mini clock widgets without full refresh."""
        for key, clock in list(state.get("clock_widgets", {}).items()):
            try:
                total = state.get("countdown_total", {}).get(key, 1)
                remaining = state.get("countdowns", {}).get(key, 0)
                if total > 0 and state.get("countdown_active", {}).get(key):
                    clock.set_progress(remaining / total)
                    clock.show()
                else:
                    clock.hide()
            except RuntimeError:
                pass  # Widget already deleted

    def countdown_tick():
        any_color_changed = False
        still_active = False
        # Only iterate keys that are actually active
        active_keys = [k for k, v in state["countdown_active"].items() if v]
        for key in active_keys:
            remaining = state["countdowns"].get(key, 0) - 1000
            state["countdowns"][key] = remaining
            if remaining <= 0:
                color = state["lights"].get(key, "green")
                if color == "yellow":
                    state["lights"][key] = "green"
                    state["countdowns"][key] = 0
                    state["countdown_active"][key] = False
                    state["counters"][key] = 0
                elif color == "red":
                    state["lights"][key] = "yellow"
                    if state.get("yellow_countdown_secs", 0) > 0:
                        state["countdowns"][key] = state["yellow_countdown_secs"] * 1000
                        state["countdown_total"][key] = state["yellow_countdown_secs"] * 1000
                        still_active = True
                    else:
                        state["countdowns"][key] = 0
                        state["countdown_active"][key] = False
                        state["counters"][key] = 0
                any_color_changed = True
            else:
                still_active = True
        if any_color_changed:
            refresh()
        elif still_active:
            _update_countdown_clocks()
        if not still_active:
            countdown_timer.stop()

    countdown_timer.timeout.connect(countdown_tick)

    def ensure_countdown_running():
        if any(state.get("countdown_active", {}).values()):
            if not countdown_timer.isActive():
                countdown_timer.start()

    def _update_student_label_only(key):
        """Update a single student's label text and clock without full refresh."""
        lbl = state.get("_label_index", {}).get(key)
        if lbl is None:
            return
        try:
            count = state.get("counters", {}).get(key, 0)
            display = f"  {key}"
            if state.get("counter_enabled") and count > 0:
                display += f" x{count}"
            lbl.set_display_text(display)
            # Ensure clock handle exists for countdown updates
            clock = state.get("clock_widgets", {}).get(key)
            if clock is None and state.get("countdown_active", {}).get(key):
                clock = _ClockHandle(lbl)
                state["clock_widgets"][key] = clock
            if clock is not None:
                total = state.get("countdown_total", {}).get(key, 1)
                remaining = state.get("countdowns", {}).get(key, 0)
                if total > 0 and state.get("countdown_active", {}).get(key):
                    clock.set_progress(remaining / total)
                    clock.show()
                else:
                    clock.hide()
        except RuntimeError:
            pass

    def on_student_click(key):
        """Handle click on student in sort mode — counter logic."""
        if not state.get("counter_enabled"):
            return
        color = state["lights"].get(key, "green")

        if color == "red":
            # Red: only reset countdown, no counter increment
            if state.get("countdown_active", {}).get(key):
                cd_secs = state["red_countdown_secs"]
                if cd_secs > 0:
                    state["countdowns"][key] = cd_secs * 1000
                    state["countdown_total"][key] = cd_secs * 1000
            _update_student_label_only(key)
            return

        state["counters"][key] = state["counters"].get(key, 0) + 1
        count = state["counters"][key]
        threshold = state["counter_to_yellow"] if color == "green" else state["counter_to_red"]

        if count >= threshold:
            # Color change — need full refresh to move student between zones
            next_color = "yellow" if color == "green" else "red"
            state["lights"][key] = next_color
            state["counters"][key] = 0
            cd_secs = state["yellow_countdown_secs"] if next_color == "yellow" else state["red_countdown_secs"]
            if cd_secs > 0:
                state["countdowns"][key] = cd_secs * 1000
                state["countdown_total"][key] = cd_secs * 1000
                state["countdown_active"][key] = True
                ensure_countdown_running()
            refresh()
        else:
            # No color change — just update label text and clock
            if state.get("countdown_active", {}).get(key):
                cd_secs = (state["yellow_countdown_secs"] if color == "yellow"
                           else state["red_countdown_secs"])
                if cd_secs > 0:
                    state["countdowns"][key] = cd_secs * 1000
                    state["countdown_total"][key] = cd_secs * 1000
            _update_student_label_only(key)

    def on_student_drop(key, new_color):
        """Handle manual drag-drop of student to a new color zone."""
        # Reset counter for this student
        state["counters"][key] = 0

        if new_color == "green":
            # Green has no countdown — clear everything
            state["countdown_active"][key] = False
            state["countdowns"][key] = 0
            state["countdown_total"][key] = 0
        elif new_color == "yellow":
            cd_secs = state.get("yellow_countdown_secs", 0)
            if cd_secs > 0:
                state["countdowns"][key] = cd_secs * 1000
                state["countdown_total"][key] = cd_secs * 1000
                state["countdown_active"][key] = True
                ensure_countdown_running()
            else:
                state["countdown_active"][key] = False
        elif new_color == "red":
            cd_secs = state.get("red_countdown_secs", 0)
            if cd_secs > 0:
                state["countdowns"][key] = cd_secs * 1000
                state["countdown_total"][key] = cd_secs * 1000
                state["countdown_active"][key] = True
                ensure_countdown_running()
            else:
                state["countdown_active"][key] = False

    def render_sort_mode():
        clear_name_widgets()
        state["clock_widgets"] = {}

        for color_name in LIGHT_ORDER:
            drop_zone = DropZoneWidget(color_name, state, refresh,
                                       click_callback=on_student_click,
                                       drop_callback=on_student_drop, parent=scroll_content)
            drop_zone.set_scroll_viewport(scroll.viewport)

            students_in_color = [s for s in state["students"] if state["lights"].get(student_key(s), "green") == color_name]
            for s in students_in_color:
                drop_zone.add_student(student_key(s))

            state["sort_zones"][color_name] = drop_zone

    def _force_panel_repaint():
        """Force the panel to repaint — works around X11 rendering artifacts.
        Nudges the window size by 1px and back to trigger Expose events."""
        try:
            geo = panel.geometry()
            panel.resize(geo.width() + 1, geo.height())
            panel.resize(geo.width(), geo.height())
        except RuntimeError:
            pass

    def refresh():
        state["_refreshing"] = True
        content.blockSignals(True)
        if state["mode"] == "click":
            render_click_mode()
        else:
            render_sort_mode()
        content.blockSignals(False)
        state["_refreshing"] = False
        # Force size cache invalidation so reflow always runs after refresh
        _last_ampel_size[0] = 0
        _last_ampel_size[1] = 0
        # Trigger a full resize/reflow after rendering widgets
        QTimer.singleShot(0, lambda: on_ampel_resize(None))
        # Force repaint on X11 after layout is recalculated
        if sys.platform != "win32":
            QTimer.singleShot(100, _force_panel_repaint)

    def set_click_mode():
        btn_click_mode.setChecked(True)
        btn_sort_mode.setChecked(False)
        state["mode"] = "click"
        refresh()

    def set_sort_mode():
        btn_click_mode.setChecked(False)
        btn_sort_mode.setChecked(True)
        state["mode"] = "sort"
        refresh()

    def reset_all():
        for s in state["students"]:
            state["lights"][student_key(s)] = "green"
        state["counters"] = {}
        state["countdowns"] = {}
        state["countdown_total"] = {}
        state["countdown_active"] = {}
        state["clock_widgets"] = {}
        countdown_timer.stop()
        refresh()

    btn_click_mode.clicked.connect(set_click_mode)
    btn_sort_mode.clicked.connect(set_sort_mode)
    btn_reset.clicked.connect(reset_all)

    def load_students(students):
        state["_key_cache"].clear()
        state["students"] = students
        for s in students:
            key = student_key(s)
            if key not in state["lights"]:
                state["lights"][key] = "green"
        refresh()

    panel.load_students = load_students
    panel.traffic_state = state
    panel.rules_green = rules_green
    panel.rules_yellow = rules_yellow
    panel.rules_red = rules_red

    # --- Main Resize Logic (on scroll, so viewport dims are current) ---
    _ampel_resize_debounce = QTimer()
    _ampel_resize_debounce.setSingleShot(True)
    _ampel_resize_debounce.setInterval(60)
    _last_ampel_size = [0, 0]

    def _do_ampel_resize():
        w = content.width()
        h = scroll.viewport().height()
        if w == _last_ampel_size[0] and h == _last_ampel_size[1]:
            return
        _last_ampel_size[0] = w
        _last_ampel_size[1] = h

        fsz = calc_name_font_size()
        apply_font_to_students(fsz)

        rule_offset = state["base_rule_size"] - 12
        rule_font_size = max(8, min(20, w // 50 + rule_offset))
        for i, text_edit in enumerate(all_rule_edits):
            font = text_edit.font()
            if font.pointSize() != rule_font_size:
                font.setPointSize(rule_font_size)
                text_edit.setFont(font)
                resizer = all_rule_resizers[i]
                QTimer.singleShot(0, resizer)
        for lbl in all_rule_labels:
            font = lbl.font()
            if font.pointSize() != rule_font_size:
                font.setPointSize(rule_font_size)
                lbl.setFont(font)

        reflow_ampel_layout()
        apply_ampel_scale()

    _ampel_resize_debounce.timeout.connect(_do_ampel_resize)

    orig_scroll_resize = scroll.resizeEvent
    def on_ampel_resize(event):
        if orig_scroll_resize and event is not None:
            orig_scroll_resize(event)
        _ampel_resize_debounce.start()
    scroll.resizeEvent = on_ampel_resize

    def change_rule_font(delta):
        state["base_rule_size"] = max(8, state["base_rule_size"] + delta)
        on_ampel_resize(None)

    btn_rule_font_up_inner.clicked.connect(lambda: change_rule_font(1))
    btn_rule_font_down_inner.clicked.connect(lambda: change_rule_font(-1))

    panel._countdown_timer = countdown_timer
    return panel


# ---------------------------------------------------------------------------
# Work Symbols Panel
# ---------------------------------------------------------------------------

WORK_SYMBOLS = [
    ("📖", "Lesen"),
    ("✏️", "Schreiben"),
    ("🤫", "Leise"),
    ("👨\u200d👩\u200d👧\u200d👦", "Gruppenarbeit"),
    ("👫", "Partnerarbeit"),
    ("👤", "Einzelarbeit"),
    ("✋", "Melden"),
    ("🎧", "Zuhören"),
    ("💬", "Diskussion"),
    ("⏸", "Pause"),
]


def create_symbols_panel():
    panel = FloatingPanel("🖼 Arbeitssymbole")
    panel.setMinimumSize(250, 150)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(10, 10, 10, 10)
    cl.setSpacing(8)

    lbl_title = QLabel("Aktive Symbole:", content)
    lbl_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent; border: none;")
    cl.addWidget(lbl_title)

    # Active display: container with HBoxLayout for emoji+label columns
    active_container = QWidget(content)
    active_container.setStyleSheet(
        "background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); "
        "border-radius: 8px; padding: 4px;"
    )
    active_layout = QHBoxLayout(active_container)
    active_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
    active_layout.setSpacing(8)
    active_layout.setContentsMargins(4, 4, 4, 4)
    cl.addWidget(active_container)

    grid = QGridLayout()
    grid.setSpacing(6)

    active_set = set()
    buttons = {}
    # Track all symbols: built-in emojis + custom images
    # Each entry: {"key": str, "emoji": str|None, "image": str|None, "label": str}
    all_symbols = [{"key": sym, "emoji": sym, "image": None, "label": label}
                   for sym, label in WORK_SYMBOLS]

    # Load custom symbols from disk
    symbols_dir = os.path.join(get_base_dir(), "symbols")
    custom_json = os.path.join(symbols_dir, "custom_symbols.json")
    custom_symbols = []
    if os.path.exists(custom_json):
        try:
            with open(custom_json, "r", encoding="utf-8") as f:
                custom_symbols = json.load(f)
        except Exception:
            custom_symbols = []

    def save_custom_symbols():
        os.makedirs(symbols_dir, exist_ok=True)
        with open(custom_json, "w", encoding="utf-8") as f:
            json.dump(custom_symbols, f, ensure_ascii=False, indent=2)

    def update_display():
        # Clear existing widgets
        while active_layout.count():
            item = active_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        active = [s for s in all_symbols if s["key"] in active_set]
        if not active:
            placeholder = QLabel("—", active_container)
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("color: white; font-size: 32px; background: transparent; border: none;")
            active_layout.addWidget(placeholder)
            return

        # Use content width minus generous margins for padding/border
        w = content.width() - 60
        h = active_container.height() - 30
        n_active = len(active)

        # Width per symbol column (account for spacing between columns)
        total_spacing = active_layout.spacing() * max(0, n_active - 1)
        col_w = max(20, (w - total_spacing) // n_active)

        # Shrink usable text width by 10% so text never touches box edges
        text_w = int(col_w * 0.90)

        # Symbol gets ~75% of height, label gets ~25%
        display_sz = max(8, min(col_w, int(h * 0.75)))

        # Binary-search for largest label font where longest label fits in text_w
        # Also cap by available height (25% of container) and proportional to display
        longest_label = max((s["label"] for s in active), key=len)
        max_label_h = max(8, int(h * 0.25))
        lo, hi, label_sz = 5, 30, 5
        while lo <= hi:
            mid = (lo + hi) // 2
            font = QFont()
            font.setPointSize(mid)
            fm = QFontMetrics(font)
            if fm.horizontalAdvance(longest_label) <= text_w and fm.height() <= max_label_h:
                label_sz = mid
                lo = mid + 1
            else:
                hi = mid - 1

        for s in active:
            col_widget = QWidget(active_container)
            col_widget.setMaximumWidth(col_w)
            col_layout = QVBoxLayout(col_widget)
            col_layout.setContentsMargins(0, 0, 0, 0)
            col_layout.setSpacing(0)
            col_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

            if s["image"] and os.path.exists(s["image"]):
                img_lbl = QLabel(col_widget)
                img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                px = QPixmap(s["image"]).scaled(
                    display_sz, display_sz,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                img_lbl.setPixmap(px)
                img_lbl.setStyleSheet("background: transparent; border: none;")
                col_layout.addWidget(img_lbl)
            else:
                sym_lbl = QLabel(s["emoji"], col_widget)
                sym_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                sym_lbl.setStyleSheet(f"color: white; font-size: {display_sz}px; background: transparent; border: none;")
                col_layout.addWidget(sym_lbl)

            txt_lbl = QLabel(s["label"], col_widget)
            txt_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            txt_lbl.setStyleSheet(
                f"color: rgba(255,255,255,180); font-size: {label_sz}pt; "
                f"background: transparent; border: none;"
            )
            col_layout.addWidget(txt_lbl)
            active_layout.addWidget(col_widget)

    def make_toggle(key):
        def toggle(checked):
            if checked:
                active_set.add(key)
            else:
                active_set.discard(key)
            update_display()
        return toggle

    sym_buttons = []

    def refresh_button_appearance(btn, sym_data):
        """Update button text/icon to match current sym_data."""
        if sym_data["image"] and os.path.exists(sym_data["image"]):
            btn.setText(f"\n{sym_data['label']}")
            btn.setIcon(QIcon(sym_data["image"]))
            btn.setIconSize(QSize(32, 32))
        else:
            btn.setText(f"{sym_data['emoji']}\n{sym_data['label']}")
            btn.setIcon(QIcon())  # clear icon

    def replace_symbol_image(sym_data, btn):
        """Replace a symbol's image via file picker."""
        file_path, _ = QFileDialog.getOpenFileName(
            content, "Bild ersetzen", "",
            "Bilder (*.png *.jpg *.jpeg *.svg *.bmp *.gif);;Alle Dateien (*)"
        )
        if not file_path:
            return
        os.makedirs(symbols_dir, exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest_name = f"replaced_{sym_data['label']}{ext}"
        dest_path = os.path.join(symbols_dir, dest_name)
        shutil.copy2(file_path, dest_path)
        sym_data["image"] = dest_path
        sym_data["emoji"] = None
        refresh_button_appearance(btn, sym_data)
        # Persist replacement for built-in symbols too
        is_custom = sym_data["key"].startswith("custom:")
        if is_custom:
            for cs in custom_symbols:
                if cs["key"] == sym_data["key"]:
                    cs["image"] = dest_path
                    break
            save_custom_symbols()
        else:
            # Save built-in replacements
            save_builtin_replacements()
        if sym_data["key"] in active_set:
            update_display()

    def delete_custom_symbol(sym_data, btn):
        """Delete a custom symbol."""
        key = sym_data["key"]
        active_set.discard(key)
        btn.setParent(None)
        btn.deleteLater()
        if key in buttons:
            del buttons[key]
        if btn in sym_buttons:
            sym_buttons.remove(btn)
        all_symbols[:] = [s for s in all_symbols if s["key"] != key]
        custom_symbols[:] = [cs for cs in custom_symbols if cs["key"] != key]
        save_custom_symbols()
        # Re-layout grid
        rebuild_grid()
        update_display()

    def rebuild_grid():
        """Re-layout all buttons in the grid after deletion."""
        w = content.width()
        num_cols = max(3, min(6, (w - 20) // 70))
        for b in sym_buttons:
            grid.removeWidget(b)
        for i, b in enumerate(sym_buttons):
            row, col = divmod(i, num_cols)
            grid.addWidget(b, row, col)

    # Persistence for built-in symbol image replacements
    builtin_json = os.path.join(symbols_dir, "builtin_replacements.json")
    def save_builtin_replacements():
        replacements = {}
        for s in all_symbols:
            if not s["key"].startswith("custom:") and s["image"]:
                replacements[s["key"]] = s["image"]
        os.makedirs(symbols_dir, exist_ok=True)
        with open(builtin_json, "w", encoding="utf-8") as f:
            json.dump(replacements, f, ensure_ascii=False, indent=2)

    def load_builtin_replacements():
        if os.path.exists(builtin_json):
            try:
                with open(builtin_json, "r", encoding="utf-8") as f:
                    replacements = json.load(f)
                for s in all_symbols:
                    if s["key"] in replacements and os.path.exists(replacements[s["key"]]):
                        s["image"] = replacements[s["key"]]
                        s["emoji"] = None
            except Exception:
                pass

    load_builtin_replacements()

    def add_symbol_button(sym_data, index):
        """Create a toggle button for a symbol and add it to the grid."""
        key = sym_data["key"]
        if sym_data["image"] and os.path.exists(sym_data["image"]):
            btn = QPushButton(f"\n{sym_data['label']}", content)
            btn.setIcon(QIcon(sym_data["image"]))
            btn.setIconSize(QSize(32, 32))
        else:
            btn = QPushButton(f"{sym_data['emoji']}\n{sym_data['label']}", content)
        btn.setCheckable(True)
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(60,60,60,200); color: white; border: 2px solid rgba(255,255,255,40);
                border-radius: 8px; padding: 4px;
            }
            QPushButton:hover { background: rgba(80,80,80,220); border: 2px solid rgba(255,255,255,80); }
            QPushButton:checked { background: rgba(0,120,215,200); border: 2px solid rgba(0,150,255,220); }
        """)
        btn.clicked.connect(make_toggle(key))
        btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        def show_context_menu(pos, sd=sym_data, b=btn):
            menu = QMenu(content)
            menu.setStyleSheet(
                "QMenu { background: rgba(50,50,50,240); color: white; border: 1px solid rgba(255,255,255,60); }"
                "QMenu::item:selected { background: rgba(0,120,215,200); }"
            )
            act_replace = menu.addAction("Bild ersetzen")
            act_delete = None
            if sd["key"].startswith("custom:"):
                act_delete = menu.addAction("Löschen")
            action = menu.exec(b.mapToGlobal(pos))
            if action == act_replace:
                replace_symbol_image(sd, b)
            elif act_delete and action == act_delete:
                delete_custom_symbol(sd, b)

        btn.customContextMenuRequested.connect(show_context_menu)
        buttons[key] = btn
        sym_buttons.append(btn)
        w = content.width() if content.width() > 0 else 300
        num_cols = max(3, min(6, (w - 20) // 70))
        row, col = divmod(index, num_cols)
        grid.addWidget(btn, row, col)
        return btn

    # Add built-in symbols
    for i, sym_data in enumerate(all_symbols):
        add_symbol_button(sym_data, i)

    # Add previously saved custom symbols
    for cs in custom_symbols:
        sym_data = {"key": cs["key"], "emoji": None, "image": cs["image"], "label": cs["label"]}
        all_symbols.append(sym_data)
        add_symbol_button(sym_data, len(all_symbols) - 1)

    # Wrap grid + add button in a container for toggling
    grid_container = QWidget(content)
    grid_container.setStyleSheet("background: transparent; border: none;")
    grid_container_layout = QVBoxLayout(grid_container)
    grid_container_layout.setContentsMargins(0, 0, 0, 0)
    grid_container_layout.setSpacing(6)
    grid_container_layout.addLayout(grid)

    # Add custom symbol button
    btn_add_custom = QPushButton("+ Eigenes Symbol", content)
    btn_add_custom.setStyleSheet(INNER_BUTTON_STYLE())
    grid_container_layout.addWidget(btn_add_custom)

    # Toggle button to show/hide the selection grid
    btn_toggle_grid = QPushButton("Symbole ausblenden", content)
    btn_toggle_grid.setStyleSheet(INNER_BUTTON_STYLE())
    def toggle_grid():
        if grid_container.isVisible():
            grid_container.hide()
            btn_toggle_grid.setText("Symbole einblenden")
        else:
            grid_container.show()
            btn_toggle_grid.setText("Symbole ausblenden")
    btn_toggle_grid.clicked.connect(toggle_grid)
    cl.addWidget(btn_toggle_grid)
    cl.addWidget(grid_container)

    def add_custom_symbol():
        file_path, _ = QFileDialog.getOpenFileName(
            content, "Bild auswählen", "",
            "Bilder (*.png *.jpg *.jpeg *.svg *.bmp *.gif);;Alle Dateien (*)"
        )
        if not file_path:
            return
        label, ok = QInputDialog.getText(content, "Symbolname", "Bezeichnung für das Symbol:")
        if not ok or not label.strip():
            return
        label = label.strip()
        # Copy image to symbols/ folder
        os.makedirs(symbols_dir, exist_ok=True)
        ext = os.path.splitext(file_path)[1]
        dest_name = f"custom_{len(custom_symbols)}_{label}{ext}"
        dest_path = os.path.join(symbols_dir, dest_name)
        shutil.copy2(file_path, dest_path)
        # Create symbol data
        key = f"custom:{dest_name}"
        cs_entry = {"key": key, "image": dest_path, "label": label}
        custom_symbols.append(cs_entry)
        save_custom_symbols()
        sym_data = {"key": key, "emoji": None, "image": dest_path, "label": label}
        all_symbols.append(sym_data)
        add_symbol_button(sym_data, len(all_symbols) - 1)

    btn_add_custom.clicked.connect(add_custom_symbol)
    cl.addStretch()

    panel.set_content_widget(content)

    _last_sym_size = [0, 0]

    def on_symbols_resize(event):
        w = content.width()
        h = content.height()
        if w == _last_sym_size[0] and h == _last_sym_size[1]:
            return
        _last_sym_size[0] = w
        _last_sym_size[1] = h
        scale = min(w, h)
        n = len(sym_buttons)
        if n == 0:
            return

        # Determine how many columns fit — use both dimensions
        num_cols = max(3, min(6, (w - 20) // 70))
        num_rows = math.ceil(n / num_cols)

        # Calculate button size to fit: width-based and height-based, pick smaller
        spacing_w = grid.spacing() * (num_cols - 1) + 20
        btn_w_from_w = (w - spacing_w) // num_cols
        # Reserve ~30% height for active display + title, rest for grid
        grid_h = max(60, int(h * 0.65))
        spacing_h = grid.spacing() * max(0, num_rows - 1)
        btn_h_from_h = (grid_h - spacing_h) // max(1, num_rows)
        btn_w_from_h = int(btn_h_from_h / 0.875)

        btn_w = max(44, min(btn_w_from_w, btn_w_from_h))
        btn_h = int(btn_w * 0.875)
        btn_font = max(7, btn_w // 8)
        icon_sz = max(12, btn_w // 3)

        # Re-layout grid with current column count
        for i, b in enumerate(sym_buttons):
            r, c = divmod(i, num_cols)
            grid.addWidget(b, r, c)

        for b in sym_buttons:
            b.setFixedSize(btn_w, btn_h)
            b.setIconSize(QSize(icon_sz, icon_sz))
            b.setStyleSheet(f"""
                QPushButton {{
                    background: rgba(60,60,60,200); color: white; border: 2px solid rgba(255,255,255,40);
                    border-radius: 8px; font-size: {btn_font}px; padding: 2px;
                }}
                QPushButton:hover {{ background: rgba(80,80,80,220); border: 2px solid rgba(255,255,255,80); }}
                QPushButton:checked {{ background: rgba(0,120,215,200); border: 2px solid rgba(0,150,255,220); }}
            """)

        # Scale title and add-button font
        title_sz = max(10, scale // 25)
        lbl_title.setStyleSheet(f"color: white; font-size: {title_sz}px; font-weight: bold; background: transparent; border: none;")
        add_btn_fsz = max(10, scale // 30)
        scalable_btn_style = (
            f"QPushButton {{ background-color: rgba(60,60,60,200); color: white; "
            f"border: 1px solid rgba(255,255,255,60); border-radius: 5px; "
            f"padding: 4px 10px; font-size: {add_btn_fsz}px; font-weight: bold; }}"
            f"QPushButton:hover {{ background-color: rgba(80,80,80,220); }}"
            f"QPushButton:pressed {{ background-color: rgba(50,50,50,255); }}"
        )
        btn_add_custom.setStyleSheet(scalable_btn_style)
        btn_toggle_grid.setStyleSheet(scalable_btn_style)

        update_display()  # Re-render active display with new sizes

    _sym_resize_debounce = QTimer()
    _sym_resize_debounce.setSingleShot(True)
    _sym_resize_debounce.setInterval(60)
    _sym_resize_debounce.timeout.connect(lambda: on_symbols_resize(None))
    orig_sym_resize = content.resizeEvent
    def sym_resize_wrapper(event):
        if orig_sym_resize:
            orig_sym_resize(event)
        _sym_resize_debounce.start()
    content.resizeEvent = sym_resize_wrapper

    return panel


# ---------------------------------------------------------------------------
# Noise Monitor Panel
# ---------------------------------------------------------------------------

class CumulativeTrafficLight(QWidget):
    """A big traffic light widget that paints 3 stacked circles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = "green"  # "green", "yellow", or "red"
        self.setMinimumSize(60, 120)

    def set_level(self, level):
        self._level = level
        self.update()

    _COLORS_ORDER = [
        ("red", QBrush(QColor("#FF4444"))),
        ("yellow", QBrush(QColor("#FFDD00"))),
        ("green", QBrush(QColor("#44DD44"))),
    ]
    _DIM_BRUSH = QBrush(QColor("#333333"))
    _CIRCLE_PEN = QPen(QColor(255, 255, 255, 60), 2)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w = self.width()
        h = self.height()
        diameter = min(w - 10, (h - 20) // 3)
        if diameter < 10:
            diameter = 10
        x_center = w // 2
        gap = (h - 3 * diameter) // 4
        painter.setPen(self._CIRCLE_PEN)
        for i, (name, bright_brush) in enumerate(self._COLORS_ORDER):
            y = gap + i * (diameter + gap)
            painter.setBrush(bright_brush if self._level == name else self._DIM_BRUSH)
            painter.drawEllipse(x_center - diameter // 2, y, diameter, diameter)
        painter.end()


# ---------------------------------------------------------------------------
# Noise Monitor Panel
# ---------------------------------------------------------------------------

def create_noise_panel():
    panel = FloatingPanel("🔊 Lautstärke-Monitor")
    panel.setMinimumSize(280, 350)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # Status label (hidden, used internally for error messages)
    status_lbl = QLabel("", content)
    status_lbl.setStyleSheet("color: white; font-size: 12px; background: transparent; border: none;")
    status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    status_lbl.hide()
    cl.addWidget(status_lbl)

    # Cumulative traffic light
    traffic_light = CumulativeTrafficLight(content)
    traffic_light.setMinimumHeight(150)
    cl.addWidget(traffic_light, stretch=1)

    # Live level display (small)
    level_lbl = QLabel("—", content)
    level_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    level_lbl.setStyleSheet(
        "color: #44DD44; font-size: 18px; font-weight: bold; "
        "background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); "
        "border-radius: 6px; padding: 4px;"
    )
    cl.addWidget(level_lbl)

    # Progress bar for live level
    level_bar = QProgressBar(content)
    level_bar.setRange(0, 100)
    level_bar.setValue(0)
    level_bar.setTextVisible(False)
    level_bar.setFixedHeight(14)
    level_bar.setStyleSheet("""
        QProgressBar {
            background: rgba(50,50,50,200);
            border: 1px solid rgba(255,255,255,40);
            border-radius: 5px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 #44DD44, stop:0.5 #FFDD00, stop:1 #FF4444);
            border-radius: 4px;
        }
    """)
    cl.addWidget(level_bar)

    # Threshold slider — always visible
    thresh_row = QHBoxLayout()
    thresh_lbl = QLabel("Schwelle:", content)
    thresh_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    thresh_slider = QSlider(Qt.Orientation.Horizontal, content)
    thresh_slider.setRange(5, 100)
    thresh_slider.setValue(50)
    thresh_slider.setStyleSheet("""
        QSlider::groove:horizontal {
            background: rgba(255,255,255,30); height: 6px; border-radius: 3px;
        }
        QSlider::handle:horizontal {
            background: white; width: 16px; margin: -5px 0; border-radius: 8px;
        }
    """)
    thresh_val_lbl = QLabel("50%", content)
    thresh_val_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none; min-width: 35px;")
    thresh_row.addWidget(thresh_lbl)
    thresh_row.addWidget(thresh_slider)
    thresh_row.addWidget(thresh_val_lbl)
    cl.addLayout(thresh_row)

    def update_thresh_label(val):
        thresh_val_lbl.setText(f"{val}%")
    thresh_slider.valueChanged.connect(update_thresh_label)

    # Collapsible settings container
    noise_settings = QWidget(content)
    noise_settings.setStyleSheet("background: transparent; border: none;")
    ns_layout = QVBoxLayout(noise_settings)
    ns_layout.setContentsMargins(0, 0, 0, 0)
    ns_layout.setSpacing(6)

    # Cumulative thresholds
    spin_style = "QSpinBox { background: rgba(50,50,50,200); color: white; border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 4px; font-size: 13px; min-width: 45px; }"
    cum_row = QHBoxLayout()
    cum_lbl_y = QLabel("Gelb ab:", content)
    cum_lbl_y.setStyleSheet("color: #FFDD00; font-size: 13px; font-weight: bold; background: transparent; border: none;")
    spin_yellow = QSpinBox(content)
    spin_yellow.setRange(1, 999)
    spin_yellow.setValue(5)
    spin_yellow.setStyleSheet(spin_style)
    cum_lbl_r = QLabel("Rot ab:", content)
    cum_lbl_r.setStyleSheet("color: #FF4444; font-size: 13px; font-weight: bold; background: transparent; border: none;")
    spin_red = QSpinBox(content)
    spin_red.setRange(1, 999)
    spin_red.setValue(10)
    spin_red.setStyleSheet(spin_style)
    cum_row.addWidget(cum_lbl_y)
    cum_row.addWidget(spin_yellow)
    cum_row.addWidget(cum_lbl_r)
    cum_row.addWidget(spin_red)
    cum_row.addStretch()
    ns_layout.addLayout(cum_row)

    # Cooldown
    cooldown_row = QHBoxLayout()
    cooldown_lbl = QLabel("Karenz:", content)
    cooldown_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    spin_cooldown = QSpinBox(content)
    spin_cooldown.setRange(1, 30)
    spin_cooldown.setValue(5)
    spin_cooldown.setSuffix(" s")
    spin_cooldown.setStyleSheet(spin_style)
    cooldown_row.addWidget(cooldown_lbl)
    cooldown_row.addWidget(spin_cooldown)
    cooldown_row.addStretch()
    ns_layout.addLayout(cooldown_row)

    # dB display toggle
    chk_show_db = QCheckBox("dB anzeigen", content)
    chk_show_db.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    chk_show_db.setChecked(False)
    ns_layout.addWidget(chk_show_db)

    # Microphone selector
    mic_row = QHBoxLayout()
    mic_lbl = QLabel("Mikrofon:", content)
    mic_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    mic_combo = QComboBox(content)
    mic_combo.setStyleSheet(
        "QComboBox { background-color: rgba(70,70,70,220); color: white; border: 1px solid rgba(255,255,255,80); "
        "border-radius: 5px; padding: 3px 8px; font-size: 12px; }"
        "QComboBox::drop-down { border: none; }"
        "QComboBox QAbstractItemView { background-color: rgba(50,50,50,240); color: white; "
        "selection-background-color: rgba(0,120,215,200); }"
    )
    if HAS_MULTIMEDIA:
        for dev in QMediaDevices.audioInputs():
            mic_combo.addItem(dev.description(), dev)
    if mic_combo.count() == 0:
        mic_combo.addItem("(Standard)", None)
    mic_row.addWidget(mic_lbl)
    mic_row.addWidget(mic_combo, 1)
    ns_layout.addLayout(mic_row)

    btn_toggle_noise_settings = QPushButton("Einstellungen ▼", content)
    btn_toggle_noise_settings.setStyleSheet(INNER_BUTTON_STYLE())
    def toggle_noise_settings():
        if noise_settings.isVisible():
            noise_settings.hide()
            btn_toggle_noise_settings.setText("Einstellungen ▶")
        else:
            noise_settings.show()
            btn_toggle_noise_settings.setText("Einstellungen ▼")
    btn_toggle_noise_settings.clicked.connect(toggle_noise_settings)
    cl.addWidget(btn_toggle_noise_settings)
    cl.addWidget(noise_settings)

    # Too loud counter
    counter_row = QHBoxLayout()
    counter_lbl = QLabel("Zu laut:", content)
    counter_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    counter_val = QLabel("0", content)
    counter_val.setStyleSheet("color: #FF4444; font-size: 18px; font-weight: bold; background: transparent; border: none;")
    btn_reset_counter = QPushButton("Reset", content)
    btn_reset_counter.setStyleSheet(INNER_BUTTON_STYLE())
    counter_row.addWidget(counter_lbl)
    counter_row.addWidget(counter_val)
    counter_row.addStretch()
    counter_row.addWidget(btn_reset_counter)
    cl.addLayout(counter_row)

    # Start/Stop toggle button
    btn_row = QHBoxLayout()
    btn_start_stop = QPushButton("Start", content)
    btn_start_stop.setStyleSheet(INNER_BUTTON_STYLE())
    btn_row.addWidget(btn_start_stop)
    cl.addLayout(btn_row)

    panel.set_content_widget(content)

    # Audio state
    audio_state = {
        "running": False,
        "source": None,
        "io_device": None,
        "too_loud_count": 0,
        "was_loud": False,
        "cumulative_level": "green",
        "cooldown_until": 0.0,
    }
    poll_timer = QTimer()
    poll_timer.setInterval(150)

    def compute_level():
        """Read available audio data and compute RMS level 0-100."""
        io = audio_state.get("io_device")
        if io is None:
            return 0
        data = io.readAll()
        if data.isEmpty():
            return 0
        raw = bytes(data.data())
        if len(raw) < 2:
            return 0
        count = len(raw) // 2
        try:
            samples = struct.unpack(f"<{count}h", raw[:count * 2])
        except struct.error:
            return 0
        if not samples:
            return 0
        rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
        level = min(100, int(rms / 327.67))
        return level

    def update_cumulative_light():
        count = audio_state["too_loud_count"]
        red_thresh = spin_red.value()
        yellow_thresh = spin_yellow.value()
        if count >= red_thresh:
            new_level = "red"
        elif count >= yellow_thresh:
            new_level = "yellow"
        else:
            new_level = "green"
        if new_level != audio_state["cumulative_level"]:
            audio_state["cumulative_level"] = new_level
            traffic_light.set_level(new_level)

    _last_noise_color = [""]

    def poll():
        level = compute_level()
        level_bar.setValue(level)
        threshold = thresh_slider.value()
        now = time.monotonic()

        if level < threshold * 0.6:
            emoji = "🟢"
            color = "#44DD44"
        elif level < threshold:
            emoji = "🟡"
            color = "#FFDD00"
        else:
            emoji = "🔴"
            color = "#FF4444"

        # Build display text with optional dB
        display_text = f"{emoji} {level}%"
        if chk_show_db.isChecked() and level > 0:
            rms_approx = level * 327.67
            if rms_approx > 0:
                db_val = 20 * math.log10(rms_approx)
                display_text = f"{emoji} {level}% ({db_val:.0f} dB)"
        level_lbl.setText(display_text)
        # Only update stylesheet when color actually changes
        if color != _last_noise_color[0]:
            _last_noise_color[0] = color
            level_lbl.setStyleSheet(
                f"color: {color}; font-size: 18px; font-weight: bold; "
                f"background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); "
                f"border-radius: 6px; padding: 4px;"
            )

        # Count "too loud" events (with cooldown)
        if level >= threshold:
            if not audio_state["was_loud"] and now >= audio_state["cooldown_until"]:
                audio_state["too_loud_count"] += 1
                counter_val.setText(str(audio_state["too_loud_count"]))
                audio_state["was_loud"] = True
                audio_state["cooldown_until"] = now + spin_cooldown.value()
                update_cumulative_light()
        else:
            audio_state["was_loud"] = False

    poll_timer.timeout.connect(poll)

    def start_monitoring():
        if audio_state["running"]:
            return
        if not HAS_MULTIMEDIA:
            status_lbl.setText("QtMultimedia nicht verfügbar")
            status_lbl.show()
            return
        try:
            fmt = QAudioFormat()
            fmt.setSampleRate(16000)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            # Use selected microphone or default
            selected_dev = mic_combo.currentData()
            device = selected_dev if selected_dev else QMediaDevices.defaultAudioInput()
            if device.isNull():
                status_lbl.setText("Kein Mikrofon gefunden")
                status_lbl.show()
                return

            source = QAudioSource(device, fmt)
            io_device = source.start()
            audio_state["source"] = source
            audio_state["io_device"] = io_device
            audio_state["running"] = True
            poll_timer.start()
            status_lbl.hide()
        except Exception as e:
            status_lbl.setText(f"Fehler: {e}")
            status_lbl.show()

    def stop_monitoring():
        poll_timer.stop()
        if audio_state["source"]:
            audio_state["source"].stop()
            audio_state["source"] = None
            audio_state["io_device"] = None
        audio_state["running"] = False
        level_bar.setValue(0)
        level_lbl.setText("—")
        _last_noise_color[0] = ""
        level_lbl.setStyleSheet(
            "color: #44DD44; font-size: 18px; font-weight: bold; "
            "background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); "
            "border-radius: 6px; padding: 4px;"
        )
        status_lbl.hide()
        btn_start_stop.setText("Start")

    def toggle_monitoring():
        if audio_state["running"]:
            stop_monitoring()
        else:
            start_monitoring()
            if audio_state["running"]:
                btn_start_stop.setText("Stop")

    def reset_counter():
        audio_state["too_loud_count"] = 0
        audio_state["cumulative_level"] = "green"
        counter_val.setText("0")
        traffic_light.set_level("green")

    btn_start_stop.clicked.connect(toggle_monitoring)
    btn_reset_counter.clicked.connect(reset_counter)

    # Stop monitoring when panel is closed
    panel.closed.connect(stop_monitoring)
    panel.minimized.connect(stop_monitoring)

    # Store threshold spinboxes for layout persistence
    panel.noise_spin_yellow = spin_yellow
    panel.noise_spin_red = spin_red

    return panel


# ---------------------------------------------------------------------------
# QR-Code Generator Panel
# ---------------------------------------------------------------------------

def create_qr_panel():
    panel = FloatingPanel("📱 QR-Code")
    panel.setMinimumSize(300, 350)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # URL input
    url_lbl = QLabel("Link:", content)
    url_lbl.setStyleSheet("color: white; font-size: 14px; font-weight: bold; background: transparent; border: none;")
    cl.addWidget(url_lbl)

    url_input = QLineEdit(content)
    url_input.setPlaceholderText("Link eingeben…")
    url_input.setStyleSheet(
        "QLineEdit { background: rgba(50,50,50,200); color: white; "
        "border: 1px solid rgba(255,255,255,60); border-radius: 4px; "
        "padding: 6px; font-size: 14px; }"
    )
    cl.addWidget(url_input)

    # Generate button
    btn_generate = QPushButton("📱 Erstellen", content)
    btn_generate.setStyleSheet(INNER_BUTTON_STYLE())
    cl.addWidget(btn_generate)

    # QR code display
    qr_display = QLabel("", content)
    qr_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
    qr_display.setStyleSheet(
        "background: white; border: 1px solid rgba(255,255,255,60); "
        "border-radius: 8px; padding: 8px; min-height: 200px;"
    )
    qr_display.setScaledContents(False)
    qr_display.original_pixmap = None  # Store the unscaled pixmap
    cl.addWidget(qr_display, stretch=1)

    # Status
    status_lbl = QLabel("", content)
    status_lbl.setStyleSheet("color: #FFDD00; font-size: 12px; background: transparent; border: none;")
    cl.addWidget(status_lbl)

    panel.set_content_widget(content)

    def scale_and_set_pixmap():
        """Scales the stored original pixmap to fit the label."""
        if not qr_display.original_pixmap:
            return
        
        # Keep a small margin
        display_size = min(qr_display.width(), qr_display.height()) - 16
        if display_size <= 0:
            return

        scaled_pixmap = qr_display.original_pixmap.scaled(
            display_size, display_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        qr_display.setPixmap(scaled_pixmap)

    def generate_qr():
        if not HAS_QRCODE:
            status_lbl.setText("⚠ qrcode nicht installiert (pip install qrcode[pil])")
            status_lbl.setStyleSheet("color: #FF4444; font-size: 12px; background: transparent; border: none;")
            return

        url = url_input.text().strip()
        if not url:
            status_lbl.setText("⚠ Bitte einen Link eingeben!")
            status_lbl.setStyleSheet("color: #FF4444; font-size: 12px; background: transparent; border: none;")
            return

        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=2)
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert PIL Image to QPixmap
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            buf.seek(0)
            qimage = QImage()
            qimage.loadFromData(buf.read())
            
            # Store original, unscaled pixmap
            qr_display.original_pixmap = QPixmap.fromImage(qimage)

            # Perform initial scaling
            scale_and_set_pixmap()

            status_lbl.setText("✅ QR-Code erstellt!")
            status_lbl.setStyleSheet("color: #44DD44; font-size: 12px; background: transparent; border: none;")
        except Exception as e:
            status_lbl.setText(f"⚠ Fehler: {e}")
            status_lbl.setStyleSheet("color: #FF4444; font-size: 12px; background: transparent; border: none;")

    # Handle resizing — override qr_display's resizeEvent so it fires
    # after the label itself has its new dimensions
    _qr_resize_debounce = QTimer()
    _qr_resize_debounce.setSingleShot(True)
    _qr_resize_debounce.setInterval(60)
    _qr_resize_debounce.timeout.connect(scale_and_set_pixmap)
    orig_qr_resize = qr_display.resizeEvent
    def on_qr_resize(event):
        if orig_qr_resize:
            orig_qr_resize(event)
        _qr_resize_debounce.start()
    qr_display.resizeEvent = on_qr_resize

    btn_generate.clicked.connect(generate_qr)
    url_input.returnPressed.connect(generate_qr)

    return panel


# ---------------------------------------------------------------------------
# Help Panel
# ---------------------------------------------------------------------------

def create_help_panel():
    panel = FloatingPanel("❓ Hilfe")
    panel.setMinimumSize(380, 300)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(4)

    scroll = QScrollArea(content)
    scroll.setWidgetResizable(True)
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")

    inner = QWidget()
    inner.setStyleSheet("background: transparent; border: none;")
    il = QVBoxLayout(inner)
    il.setContentsMargins(8, 8, 8, 8)
    il.setSpacing(6)

    help_sections = [
        ("⌨️ Tastenkürzel", [
            "Esc / Ctrl+Q — Overlay beenden",
            "Ctrl+B — Fett (im Texteditor)",
            "Ctrl+I — Kursiv (im Texteditor)",
            "Ctrl+U — Unterstrichen (im Texteditor)",
            "Ctrl+Shift+W — Weißer Hintergrund ein/aus",
        ]),
        ("🖱️ Fenster-Bedienung", [
            "Oberer Rand hovern — Titelleiste mit Buttons einblenden",
            "Titelleiste ziehen — Fenster verschieben",
            "Ränder/Ecken ziehen — Fenster skalieren",
            "▬ Button — Fenster minimieren/maximieren",
            "✕ Button — Fenster schließen",
            "Toolbar-Buttons — Fenster ein-/ausblenden",
        ]),
        ("📚 Klassen", [
            "Klasse über '📚 Klasse' in der Toolbar wählen",
            "Klassendateien liegen im 'classes/' Ordner als JSON",
            "Format: {\"class_name\": \"5a\", \"students\": [{\"first_name\": \"...\", \"last_name\": \"...\"}]}",
        ]),
        ("📝 Texteditor", [
            "Formatierungsleiste ein-/ausklappbar",
            "Schriftgrößen von 10 bis 72",
            "Textfarben und Markierungsfarben wählbar",
            "Blinken: Text markieren → Blinken-Button → Dauer wählen",
            "Blinken stoppen: Ohne Markierung auf Blinken klicken",
        ]),
        ("🚦 Ampelsystem", [
            "Klick: Auf den Punkt klicken um Farbe zu wechseln",
            "Sortieren: Namen per Drag & Drop zwischen Farben verschieben",
            "'Alle auf Grün' setzt alle zurück",
            "Regeln einklappbar, Schriftgröße per +/− anpassbar",
        ]),
        ("⏱ Timer / Stoppuhr", [
            "Modus wählen: Timer oder Stoppuhr",
            "Start/Pause als ein Toggle-Button",
            "+/− Buttons zum schnellen Anpassen der Zeit",
            "Alarmton bei Ablauf (konfigurierbar in Einstellungen)",
        ]),
        ("🔊 Lautstärke-Monitor", [
            "Misst die Umgebungslautstärke über das Mikrofon",
            "Mikrofon in den Einstellungen wählbar",
            "Schwelle per Slider einstellen (immer sichtbar)",
            "Karenzzeit: Sekunden bis zur nächsten Zählung",
            "dB-Anzeige optional aktivierbar",
            "Zählt wie oft es 'zu laut' war (Gelb/Rot-Schwellen einstellbar)",
        ]),
        ("⬜ Weißer Hintergrund", [
            "Blendet alles außer dem Overlay aus",
            "Per Button oder Ctrl+Shift+W ein-/ausschalten",
        ]),
        ("🧹 Aufräumen", [
            "Zeigt Aufräum-Anweisungen als Vollbild-Overlay",
            "Rechtsklick auf den Button → Text bearbeiten (mit Formatierung)",
            "Linksklick → Aufräum-Overlay anzeigen/ausblenden",
        ]),
        ("💾 Layouts", [
            "Layouts werden automatisch beim Beenden gespeichert",
            "Beim Start wird das letzte Layout wiederhergestellt",
            "Pro Klasse wird ein eigenes Layout gespeichert",
            "Texteditor-Inhalt wird mitgespeichert",
            "Layout-Dateien liegen im 'layouts/' Ordner",
        ]),
        ("⬇ Minimieren", [
            "⬇ Button — alles ausblenden",
            "◀ Button — nur Toolbar-Buttons einklappen",
            "Blauer ▲ Button erscheint zum Wiederherstellen",
        ]),
    ]

    for section_title, items in help_sections:
        # Clickable header to toggle section
        header_btn = QPushButton(f"{section_title} ▶", inner)
        header_btn.setStyleSheet(
            "QPushButton { color: #4488FF; font-size: 15px; font-weight: bold; "
            "background: transparent; border: none; padding-top: 4px; text-align: left; }"
            "QPushButton:hover { color: #66AAFF; }"
        )
        il.addWidget(header_btn)

        # Collapsible content container (hidden by default)
        section_widget = QWidget(inner)
        section_widget.setStyleSheet("background: transparent; border: none;")
        section_layout = QVBoxLayout(section_widget)
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(2)
        for item in items:
            lbl = QLabel(f"  • {item}", section_widget)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                "color: rgba(255,255,255,200); font-size: 13px; "
                "background: transparent; border: none; padding: 1px 8px;"
            )
            section_layout.addWidget(lbl)
        section_widget.hide()
        il.addWidget(section_widget)

        def make_toggle(btn, widget, title):
            def toggle():
                if widget.isVisible():
                    widget.hide()
                    btn.setText(f"{title} ▶")
                else:
                    widget.show()
                    btn.setText(f"{title} ▼")
            return toggle
        header_btn.clicked.connect(make_toggle(header_btn, section_widget, section_title))

    il.addStretch()
    scroll.setWidget(inner)
    cl.addWidget(scroll)

    panel.set_content_widget(content)
    return panel


# ---------------------------------------------------------------------------
# CleanupOverlay – fullscreen white overlay with cleanup instructions
# ---------------------------------------------------------------------------

class CleanupOverlay(QWidget):
    """Fullscreen white overlay showing cleanup instructions."""
    closed = pyqtSignal()

    def __init__(self, get_students_fn=None):
        super().__init__()
        self._html = ""
        self._get_students_fn = get_students_fn
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet("background: white;")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)

        self._label = QLabel("", self)
        self._label.setWordWrap(True)
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setStyleSheet("color: black; font-size: 36px; background: white; border: none;")
        layout.addWidget(self._label, 1)

        # --- Ordnungsdienst section ---
        duty_container = QWidget(self)
        duty_container.setStyleSheet("background: white; border: none;")
        duty_layout = QHBoxLayout(duty_container)
        duty_layout.setContentsMargins(0, 10, 0, 10)
        duty_layout.setSpacing(12)

        self._duty_label = QLabel("", duty_container)
        self._duty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._duty_label.setStyleSheet(
            "color: #333; font-size: 28px; font-weight: bold; background: white; border: none;")
        duty_layout.addWidget(self._duty_label, 1)

        btn_reroll = QPushButton("🔄", duty_container)
        btn_reroll.setStyleSheet(
            "QPushButton { background: rgba(0,120,215,220); color: white; border: none; "
            "border-radius: 6px; padding: 8px 14px; font-size: 22px; }"
            "QPushButton:hover { background: rgba(0,140,235,240); }"
        )
        btn_reroll.setToolTip("Neue Schüler ziehen")
        btn_reroll.setFixedSize(48, 48)
        btn_reroll.clicked.connect(self._reroll_duty)
        duty_layout.addWidget(btn_reroll)

        layout.addWidget(duty_container, 0, Qt.AlignmentFlag.AlignCenter)

        btn_close = QPushButton("Fertig", self)
        btn_close.setStyleSheet(
            "QPushButton { background: rgba(0,120,215,220); color: white; border: none; "
            "border-radius: 8px; padding: 12px 40px; font-size: 18px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(0,140,235,240); }"
        )
        btn_close.setFixedHeight(50)
        btn_close.clicked.connect(self._on_close)
        layout.addWidget(btn_close, 0, Qt.AlignmentFlag.AlignCenter)

    def set_html(self, html):
        self._html = html
        self._label.setText(html)
        self._label.setTextFormat(Qt.TextFormat.RichText)

    def get_html(self):
        return self._html

    def move_to_screen(self, screen_geo):
        """Move the cleanup overlay to a different screen."""
        self.setGeometry(screen_geo)

    def _reroll_duty(self):
        if not self._get_students_fn:
            self._duty_label.setText("")
            return
        result = self._get_students_fn()
        if not result:
            self._duty_label.setText("")
            return
        _, students = result
        if not students:
            self._duty_label.setText("")
            return
        import random as _rnd
        names = [f"{s.get('first_name', '')} {s.get('last_name', '')}" for s in students]
        count = min(2, len(names))
        chosen = _rnd.sample(names, count)
        self._duty_label.setText("🧹 Ordnungsdienst: " + "  &  ".join(chosen))

    def show(self):
        self._reroll_duty()
        super().show()

    def _on_close(self):
        self.hide()
        self.closed.emit()


# ---------------------------------------------------------------------------
# StudentNotesDialog – view/add/delete student notes
# ---------------------------------------------------------------------------

class StudentNotesDialog(QWidget):
    """Dialog for viewing/adding/removing notes on a student."""

    def __init__(self, student_key, class_name, parent=None):
        super().__init__(parent)
        self._student_key = student_key
        self._class_name = class_name
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setMinimumSize(360, 320)
        self.setStyleSheet(
            f"QWidget {{ background-color: rgba(25,25,30,240); "
            f"border: 1px solid {CARD_BORDER}; border-radius: 10px; }}")
        self._drag_pos = None
        self._build_ui()
        self._refresh_notes()
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen.width() // 2 - 180, screen.height() // 2 - 160, 360, 320)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        # Header
        header = QLabel(f"📝 Notizen: {self._student_key}", self)
        header.setStyleSheet(
            "color: white; font-size: 15px; font-weight: bold; "
            "background: transparent; border: none;")
        layout.addWidget(header)

        # Existing notes scroll area
        self._notes_scroll = QScrollArea(self)
        self._notes_scroll.setWidgetResizable(True)
        self._notes_scroll.setStyleSheet(
            f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE()}")
        self._notes_container = QWidget()
        self._notes_container.setStyleSheet("background: transparent; border: none;")
        self._notes_layout = QVBoxLayout(self._notes_container)
        self._notes_layout.setContentsMargins(0, 0, 0, 0)
        self._notes_layout.setSpacing(4)
        self._notes_layout.addStretch()
        self._notes_scroll.setWidget(self._notes_container)
        layout.addWidget(self._notes_scroll, 1)

        # Separator
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,40); border: none;")
        layout.addWidget(sep)

        # New note input
        self._text_input = QTextEdit(self)
        self._text_input.setMaximumHeight(50)
        self._text_input.setPlaceholderText("Neue Notiz...")
        self._text_input.setStyleSheet(
            "QTextEdit { background: rgba(40,40,40,200); color: white; "
            "border: 1px solid rgba(255,255,255,50); border-radius: 4px; "
            "padding: 4px; font-size: 13px; }")
        layout.addWidget(self._text_input)

        # Duration row
        dur_row = QHBoxLayout()
        dur_row.setSpacing(6)
        dur_lbl = QLabel("Unterrichtsstunden:", self)
        dur_lbl.setStyleSheet("color: white; font-size: 12px; background: transparent; border: none;")
        dur_row.addWidget(dur_lbl)
        self._dur_spin = QSpinBox(self)
        self._dur_spin.setRange(1, 52)
        self._dur_spin.setValue(4)
        self._dur_spin.setStyleSheet(
            "QSpinBox { background: rgba(40,40,40,200); color: white; "
            "border: 1px solid rgba(255,255,255,50); border-radius: 4px; "
            "padding: 4px; font-size: 13px; }")
        dur_row.addWidget(self._dur_spin)
        dur_row.addStretch()
        layout.addLayout(dur_row)

        # Buttons row
        btn_row = QHBoxLayout()
        btn_add = QPushButton("Hinzufügen", self)
        btn_add.setStyleSheet(INNER_BUTTON_STYLE())
        btn_add.clicked.connect(self._add_note)
        btn_row.addWidget(btn_add)

        btn_close = QPushButton("Schließen", self)
        btn_close.setStyleSheet(INNER_BUTTON_STYLE())
        btn_close.clicked.connect(self.close)
        btn_row.addWidget(btn_close)
        layout.addLayout(btn_row)

    def _refresh_notes(self):
        # Clear existing note widgets (keep the stretch)
        while self._notes_layout.count() > 1:
            item = self._notes_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        notes = load_student_notes(self._class_name)
        active = get_active_notes(self._student_key, notes)
        if not active:
            lbl = QLabel("Keine aktiven Notizen.", self._notes_container)
            lbl.setStyleSheet("color: rgba(255,255,255,120); font-size: 12px; "
                              "background: transparent; border: none;")
            self._notes_layout.insertWidget(0, lbl)
            return

        all_notes = notes.get(self._student_key, [])
        for i, n in enumerate(active):
            row = QWidget(self._notes_container)
            row.setStyleSheet("background: rgba(255,255,255,8); border-radius: 4px; border: none;")
            rl = QHBoxLayout(row)
            rl.setContentsMargins(6, 4, 6, 4)
            rl.setSpacing(6)

            remaining = n.get("_remaining", "?")
            txt = QLabel(f"{n['text']}  ({remaining} UStd.)", row)
            txt.setWordWrap(True)
            txt.setStyleSheet("color: white; font-size: 12px; background: transparent; border: none;")
            rl.addWidget(txt, 1)

            # Find the original index in the full list for deletion
            orig_idx = None
            for j, orig in enumerate(all_notes):
                if orig.get("text") == n["text"] and orig.get("created") == n["created"]:
                    orig_idx = j
                    break

            btn_del = QPushButton("✕", row)
            btn_del.setFixedSize(24, 24)
            btn_del.setStyleSheet(
                "QPushButton { background: rgba(180,40,40,180); color: white; "
                "border: none; border-radius: 4px; font-size: 12px; font-weight: bold; }"
                "QPushButton:hover { background: rgba(220,60,60,220); }")
            btn_del.clicked.connect(lambda checked, idx=orig_idx: self._delete_note(idx))
            rl.addWidget(btn_del)

            self._notes_layout.insertWidget(self._notes_layout.count() - 1, row)

    def _add_note(self):
        from datetime import date
        text = self._text_input.toPlainText().strip()
        if not text:
            return
        notes = load_student_notes(self._class_name)
        notes.setdefault(self._student_key, []).append({
            "text": text,
            "created": date.today().isoformat(),
            "duration_weeks": self._dur_spin.value(),
        })
        save_student_notes(self._class_name, notes)
        self._text_input.clear()
        self._refresh_notes()

    def _delete_note(self, index):
        if index is None:
            return
        notes = load_student_notes(self._class_name)
        student_notes = notes.get(self._student_key, [])
        if 0 <= index < len(student_notes):
            student_notes.pop(index)
            if not student_notes:
                notes.pop(self._student_key, None)
            save_student_notes(self._class_name, notes)
        self._refresh_notes()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.pos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)


# ---------------------------------------------------------------------------
# PauseOverlay – fullscreen pause with countdown
# ---------------------------------------------------------------------------

class PauseOverlay(QWidget):
    """Fullscreen colored overlay with 5-min countdown. Pauses all timers."""
    finished = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._countdown_secs = 300  # 5 minutes
        self._paused_timers = []  # list of (QTimer, was_active, state_dict) tuples
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setStyleSheet("background: rgba(0, 80, 160, 230);")
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.addStretch(1)

        self._title_label = QLabel("PAUSE", self)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._title_label.setStyleSheet(
            "color: white; font-size: 72px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(self._title_label)

        self._countdown_label = QLabel("05:00", self)
        self._countdown_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._countdown_label.setStyleSheet(
            "color: white; font-size: 120px; font-weight: bold; background: transparent; border: none;")
        layout.addWidget(self._countdown_label)

        layout.addStretch(1)

        btn_end = QPushButton("Pause beenden", self)
        btn_end.setStyleSheet(
            "QPushButton { background: rgba(255,255,255,40); color: white; border: 2px solid white; "
            "border-radius: 8px; padding: 12px 40px; font-size: 22px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(255,255,255,80); }"
        )
        btn_end.clicked.connect(self._end_pause)
        layout.addWidget(btn_end, 0, Qt.AlignmentFlag.AlignCenter)

        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(1000)
        self._tick_timer.timeout.connect(self._tick)

    def start_pause(self, timer_refs):
        """timer_refs: list of (QTimer, state_dict_or_None) tuples."""
        self._countdown_secs = 300
        self._paused_timers = []
        for qtimer, state_dict in timer_refs:
            was_active = qtimer.isActive()
            if was_active:
                qtimer.stop()
            self._paused_timers.append((qtimer, was_active, state_dict))
            if state_dict and "running" in state_dict:
                state_dict["_was_running"] = state_dict["running"]
                state_dict["running"] = False
        self._update_display()
        self.show()
        self.raise_()
        self._tick_timer.start()

    def _tick(self):
        self._countdown_secs -= 1
        self._update_display()
        if self._countdown_secs <= 0:
            self._end_pause()

    def _update_display(self):
        m, s = divmod(max(0, self._countdown_secs), 60)
        self._countdown_label.setText(f"{m:02d}:{s:02d}")

    def _end_pause(self):
        self._tick_timer.stop()
        for qtimer, was_active, state_dict in self._paused_timers:
            if was_active:
                qtimer.start()
                if state_dict and "_was_running" in state_dict:
                    state_dict["running"] = state_dict.pop("_was_running")
        self._paused_timers = []
        self.hide()
        self.finished.emit()

    def move_to_screen(self, screen_geo):
        self.setGeometry(screen_geo)


# ---------------------------------------------------------------------------
# OverlayBackground – invisible click-through
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# DrawingOverlay – draw on screen
# ---------------------------------------------------------------------------

class DrawingOverlay(QWidget):
    """Transparent fullscreen overlay for freehand drawing."""
    closed = pyqtSignal()

    COLORS = {
        "Rot": QColor(255, 60, 60),
        "Blau": QColor(60, 100, 255),
        "Grün": QColor(60, 200, 60),
        "Gelb": QColor(255, 220, 0),
        "Weiß": QColor(255, 255, 255),
        "Schwarz": QColor(0, 0, 0),
    }
    WIDTHS = {"Dünn": 2, "Mittel": 5, "Dick": 10}

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        screen = QApplication.primaryScreen().geometry()
        self.setGeometry(screen)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Canvas created lazily on first show (avoids ~8-33MB pixmap when drawing unused)
        self._canvas = None
        self._screen_size = screen.size()
        self._current_path = None
        self._pen_color = self.COLORS["Rot"]
        self._pen_width = self.WIDTHS["Mittel"]
        self._eraser = False

        # Toolbar at bottom
        self._toolbar = QWidget(self)
        self._toolbar.setStyleSheet("background: rgba(20,20,20,220); border-radius: 8px;")
        tb = QHBoxLayout(self._toolbar)
        tb.setContentsMargins(8, 4, 8, 4)
        tb.setSpacing(4)

        for name, color in self.COLORS.items():
            btn = QPushButton("", self._toolbar)
            btn.setFixedSize(24, 24)
            btn.setStyleSheet(
                f"QPushButton {{ background: {color.name()}; border: 2px solid rgba(255,255,255,120); border-radius: 4px; }}"
                f"QPushButton:hover {{ border: 2px solid white; }}"
            )
            btn.clicked.connect(lambda _checked, c=color: self._set_color(c))
            tb.addWidget(btn)

        sep = QFrame(self._toolbar)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,40);")
        tb.addWidget(sep)

        for name, w in self.WIDTHS.items():
            btn = QPushButton(name, self._toolbar)
            btn.setStyleSheet(INNER_BUTTON_STYLE())
            btn.clicked.connect(lambda _checked, width=w: self._set_width(width))
            tb.addWidget(btn)

        sep2 = QFrame(self._toolbar)
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color: rgba(255,255,255,40);")
        tb.addWidget(sep2)

        btn_eraser = QPushButton("Radierer", self._toolbar)
        btn_eraser.setCheckable(True)
        btn_eraser.setStyleSheet(FORMAT_BUTTON_STYLE())
        btn_eraser.clicked.connect(lambda checked: setattr(self, '_eraser', checked))
        tb.addWidget(btn_eraser)

        btn_clear = QPushButton("Alles löschen", self._toolbar)
        btn_clear.setStyleSheet(INNER_BUTTON_STYLE())
        btn_clear.clicked.connect(self._clear_all)
        tb.addWidget(btn_clear)

        btn_done = QPushButton("Fertig", self._toolbar)
        btn_done.setStyleSheet(
            "QPushButton { background: rgba(0,120,215,220); color: white; border: none; "
            "border-radius: 4px; padding: 5px 14px; font-size: 13px; font-weight: bold; }"
            "QPushButton:hover { background: rgba(0,140,235,240); }"
        )
        btn_done.clicked.connect(self._finish)
        tb.addWidget(btn_done)

        self._toolbar.adjustSize()
        screen = QApplication.primaryScreen().geometry()
        tw = self._toolbar.sizeHint().width()
        self._toolbar.setGeometry(
            (screen.width() - tw) // 2, screen.height() - 60, tw, 44
        )

    def _set_color(self, color):
        self._pen_color = color
        self._eraser = False

    def _set_width(self, width):
        self._pen_width = width

    def _ensure_canvas(self):
        if self._canvas is None:
            self._canvas = QPixmap(self._screen_size)
            self._canvas.fill(QColor(0, 0, 0, 0))

    def _clear_all(self):
        self._ensure_canvas()
        self._canvas.fill(QColor(0, 0, 0, 0))
        self.update()

    def _finish(self):
        self.hide()
        self.closed.emit()

    def move_to_screen(self, screen_geo):
        """Move the drawing overlay to a different screen."""
        self.setGeometry(screen_geo)
        self._screen_size = screen_geo.size()
        # Recreate canvas for new screen size (clears existing drawings)
        if self._canvas is not None:
            self._canvas = QPixmap(self._screen_size)
            self._canvas.fill(QColor(0, 0, 0, 0))
        # Reposition toolbar at bottom-center of new screen
        tw = self._toolbar.sizeHint().width()
        self._toolbar.setGeometry(
            (screen_geo.width() - tw) // 2, screen_geo.height() - 60, tw, 44
        )

    def _commit_path_to_canvas(self, path_data):
        """Render a completed stroke onto the canvas pixmap."""
        self._ensure_canvas()
        path, color, width = path_data
        p = QPainter(self._canvas)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if color.alpha() == 0:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
        else:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
        p.setPen(QPen(color if color.alpha() > 0 else QColor(0, 0, 0, 0), width,
                      Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
        p.drawPath(path)
        p.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            path = QPainterPath()
            path.moveTo(event.position())
            if self._eraser:
                self._current_path = (path, QColor(0, 0, 0, 0), self._pen_width * 3)
            else:
                self._current_path = (path, QColor(self._pen_color), self._pen_width)

    def mouseMoveEvent(self, event):
        if self._current_path:
            self._current_path[0].lineTo(event.position())
            # Only repaint the area around the current stroke tip
            pos = event.position().toPoint()
            w = self._current_path[2] + 4
            self.update(pos.x() - w, pos.y() - w, w * 2, w * 2)

    def mouseReleaseEvent(self, event):
        if self._current_path:
            self._commit_path_to_canvas(self._current_path)
            self._current_path = None
            self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        # Nearly invisible background so widget captures mouse events
        p.fillRect(self.rect(), QColor(0, 0, 0, 1))
        # Draw cached canvas (all completed strokes)
        if self._canvas:
            p.drawPixmap(0, 0, self._canvas)
        # Draw current stroke live
        if self._current_path:
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            path, color, width = self._current_path
            if color.alpha() == 0:
                p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.setPen(QPen(color if color.alpha() > 0 else QColor(0, 0, 0, 0), width,
                          Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            p.drawPath(path)
        p.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self._finish()


class OverlayBackground(QWidget):
    def __init__(self):
        super().__init__()
        self._white_mode = False
        self._bg_color = QColor(255, 255, 255, 255)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(QApplication.primaryScreen().geometry())
        QTimer.singleShot(0, self._set_click_through)
        self._on_quit = QApplication.instance().quit
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(self._handle_esc)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(self._on_quit)

    def _handle_esc(self):
        if self._white_mode:
            self.set_white_mode(False)
            self.esc_white_off.emit()
        else:
            self._on_quit()

    esc_white_off = pyqtSignal()

    def _set_click_through(self):
        if sys.platform == "win32":
            import ctypes
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x00080000 | 0x00000020)
        else:
            self._x11_set_input_shape(empty=True)

    def _remove_click_through(self):
        if sys.platform == "win32":
            import ctypes
            hwnd = int(self.winId())
            style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
            style &= ~0x00000020  # Remove WS_EX_TRANSPARENT
            ctypes.windll.user32.SetWindowLongW(hwnd, -20, style)
            SWP_NOMOVE = 0x0002
            SWP_NOSIZE = 0x0001
            SWP_NOZORDER = 0x0004
            SWP_FRAMECHANGED = 0x0020
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0,
                                              SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED)
        else:
            self._x11_set_input_shape(empty=False)

    def _x11_set_input_shape(self, empty=True):
        """Set or reset X11 input shape to make the window click-through."""
        try:
            import Xlib, Xlib.display, Xlib.X
            from Xlib.ext import shape as xshape
            d = Xlib.display.Display()
            xwin = d.create_resource_object('window', int(self.winId()))
            if empty:
                # Empty input shape = clicks pass through
                xwin.shape_rectangles(xshape.SO.Set, xshape.SK.Input, 0, 0, 0, [])
            else:
                # Reset input shape = accept all input
                xwin.shape_mask(xshape.SO.Set, xshape.SK.Input, 0, 0, Xlib.X.NONE)
            d.flush()
            d.close()
        except Exception:
            pass  # Graceful fallback if python-xlib not available

    def set_bg_color(self, color):
        self._bg_color = QColor(color)
        if self._white_mode:
            self.update()

    def set_white_mode(self, enabled):
        self._white_mode = enabled
        if enabled:
            # If 2+ screens: cover second screen only; otherwise primary
            screens = QApplication.screens()
            target = screens[1].geometry() if len(screens) > 1 else screens[0].geometry()
            self.setGeometry(target)
        else:
            self.setGeometry(QApplication.primaryScreen().geometry())
        if enabled:
            self._remove_click_through()
        else:
            self._set_click_through()
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        if self._white_mode:
            p.fillRect(self.rect(), self._bg_color)
        else:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            p.fillRect(self.rect(), QColor(0, 0, 0, 0))
        p.end()


# ---------------------------------------------------------------------------
# Layout Save / Load
# ---------------------------------------------------------------------------

def get_layout_filepath(class_name=None):
    """Return the layout JSON filepath for a given class (or default)."""
    layouts_dir = get_layouts_dir()
    if class_name:
        safe_name = "".join(c if c.isalnum() else "_" for c in class_name)
        return os.path.join(layouts_dir, f"layout_{safe_name}.json")
    return os.path.join(layouts_dir, "layout_default.json")


def save_layout(panels, toolbar, text_html, traffic_lights, class_name=None,
                ampel_rules="", noise_thresholds=None, ampel_counter_settings=None):
    """Save current layout to JSON."""
    data = {
        "class_name": class_name,
        "toolbar": {
            "x": toolbar.x(),
            "y": toolbar.y(),
            "width": toolbar.width(),
        },
        "panels": {},
        "text_content": text_html,
        "traffic_lights": traffic_lights,
        "ampel_rules": ampel_rules,
        "noise_thresholds": noise_thresholds or {"yellow": 5, "red": 10},
        "ampel_counter_settings": ampel_counter_settings or {},
    }
    for pid, panel in panels.items():
        data["panels"][pid] = {
            "x": panel.x(),
            "y": panel.y(),
            "width": panel.width(),
            "height": panel.height(),
            "visible": panel.isVisible(),
            "minimized": panel._is_minimized,
        }
    filepath = get_layout_filepath(class_name)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving layout: {e}")

    # Also save which class was last used
    meta_path = os.path.join(get_layouts_dir(), "_last_session.json")
    try:
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump({"last_class": class_name}, f, ensure_ascii=False)
    except Exception:
        pass


def save_app_settings(bg_color=None):
    """Save global app settings (not class-specific)."""
    settings_path = os.path.join(get_layouts_dir(), "_settings.json")
    data = {}
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            pass
    if bg_color:
        data["bg_color"] = bg_color.name()
    try:
        with open(settings_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def load_app_settings():
    """Load global app settings."""
    settings_path = os.path.join(get_layouts_dir(), "_settings.json")
    if os.path.exists(settings_path):
        try:
            with open(settings_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


def load_layout(class_name=None):
    """Load layout from JSON. Returns dict or None."""
    filepath = get_layout_filepath(class_name)
    if not os.path.exists(filepath):
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading layout: {e}")
        return None


def load_last_session_class():
    """Return the class name from the last session, or None."""
    meta_path = os.path.join(get_layouts_dir(), "_last_session.json")
    if not os.path.exists(meta_path):
        return None
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("last_class")
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Student Notes Persistence
# ---------------------------------------------------------------------------

def get_notes_filepath(class_name):
    safe_name = "".join(c if c.isalnum() else "_" for c in (class_name or "default"))
    return os.path.join(get_layouts_dir(), f"notes_{safe_name}.json")


def load_student_notes(class_name):
    fp = get_notes_filepath(class_name)
    if not os.path.exists(fp):
        return {}
    try:
        with open(fp, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_student_notes(class_name, notes_dict):
    fp = get_notes_filepath(class_name)
    try:
        with open(fp, "w", encoding="utf-8") as f:
            json.dump(notes_dict, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving notes: {e}")


def get_active_notes(student_key, notes_dict):
    from datetime import date, timedelta
    today = date.today()
    notes = notes_dict.get(student_key, [])
    active = []
    for n in notes:
        try:
            created = date.fromisoformat(n["created"])
            expiry = created + timedelta(days=n["duration_weeks"] * 7)
            if today <= expiry:
                days_left = (expiry - today).days
                remaining = max(0, (days_left + 6) // 7)  # ceiling division
                entry = dict(n)
                entry["_remaining"] = remaining
                active.append(entry)
        except Exception:
            continue
    return active


def cleanup_expired_notes(notes_dict):
    from datetime import date, timedelta
    today = date.today()
    for key in list(notes_dict.keys()):
        notes_dict[key] = [
            n for n in notes_dict[key]
            if today <= date.fromisoformat(n["created"]) + timedelta(days=n["duration_weeks"] * 7)
        ]
        if not notes_dict[key]:
            del notes_dict[key]
    return notes_dict


# ---------------------------------------------------------------------------
# Main Application Controller
# ---------------------------------------------------------------------------

class OverlayApp:
    def __init__(self):
        self.app = QApplication.instance()
        screen = QApplication.primaryScreen().geometry()
        self._loaded_students = None  # (class_name, [students])
        self._loaded_class_name = None
        self._loaded_class_filepath = None
        self._visible_before_minimize = []

        # Background
        self.background = OverlayBackground()
        # Restore saved background color
        app_settings = load_app_settings()
        if app_settings.get("bg_color"):
            self.background.set_bg_color(QColor(app_settings["bg_color"]))

        # Toolbar — auto-sized and centered after all buttons are added
        self.toolbar = OverlayToolbar()
        self.toolbar.move(50, 8)  # temporary position, will be centered later

        # Panels — sizes scaled for smaller screens
        sw, sh = screen.width(), screen.height()

        self.text_panel = create_text_editor_panel()
        self.text_panel.setGeometry(S(300), S(70), S(850), sh - S(140))

        self.student_panel = create_student_list_panel()
        self.student_panel.setGeometry(S(30), S(70), S(260), sh - S(140))

        self.timer_panel = create_timer_panel()
        self.timer_panel.setGeometry(sw - S(370), S(70), S(340), S(300))

        self.random_panel = create_random_panel(self._get_students)
        self.random_panel.setGeometry(sw - S(400), S(400), S(360), S(450))

        self.traffic_panel = create_traffic_light_panel(self._get_students)
        self.traffic_panel.setGeometry(S(30), S(70), S(300), sh - S(140))
        if hasattr(self.traffic_panel, 'traffic_state'):
            self.traffic_panel.traffic_state["_notes_getter"] = self._get_student_active_notes

        self.symbols_panel = create_symbols_panel()
        self.symbols_panel.setGeometry(sw // 2 - S(200), sh // 2 - S(150), S(440), S(300))


        self.noise_panel = create_noise_panel()
        self.noise_panel.setGeometry(sw - S(350), sh - S(350), S(320), S(300))

        self.qr_panel = create_qr_panel()
        self.qr_panel.setGeometry(sw // 2 - S(175), sh // 2 - S(200), S(350), S(400))

        self.help_panel = create_help_panel()
        self.help_panel.setGeometry(sw // 2 - S(220), S(80), S(440), S(500))

        # Cleanup overlay (hidden initially)
        self.cleanup_overlay = CleanupOverlay(get_students_fn=self._get_students)
        self.cleanup_overlay.set_html("<b>Bitte aufräumen!</b>")
        self.cleanup_overlay.hide()
        self.cleanup_overlay.closed.connect(lambda: self.toolbar.set_button_checked("cleanup", False))

        # Pause overlay (hidden initially)
        self.pause_overlay = PauseOverlay()
        self.pause_overlay.hide()
        self.pause_overlay.finished.connect(lambda: self.toolbar.set_button_checked("pause", False))

        # Drawing overlay (hidden initially)
        self.drawing_overlay = DrawingOverlay()
        self.drawing_overlay.hide()
        self.drawing_overlay.closed.connect(lambda: self.toolbar.set_button_checked("draw", False))

        # Restore button (hidden initially)
        self.restore_btn = RestoreButton()
        self.restore_btn.setGeometry(sw // 2 - S(24), 4, S(48), S(48))
        self.restore_btn.clicked.connect(self._restore_all)
        self.restore_btn.hide()

        # When toolbar collapses, show restore button; when expands, hide it
        def on_toolbar_collapsed(is_collapsed):
            if is_collapsed:
                self.restore_btn.show()
                self.restore_btn.raise_()
            else:
                if not self.toolbar.isVisible():
                    return  # Don't hide if everything is minimized
                self.restore_btn.hide()
        self.toolbar.collapsed.connect(on_toolbar_collapsed)

        # All panels dict for easy management
        self._panels = {
            "text_editor": self.text_panel,
            "student_list": self.student_panel,
            "timer": self.timer_panel,
            "random_name": self.random_panel,
            "traffic_light": self.traffic_panel,
            "symbols": self.symbols_panel,
            "noise_monitor": self.noise_panel,
            "qr_code": self.qr_panel,
            "help": self.help_panel,
        }

        # Toolbar buttons
        self.toolbar.add_panel_button("text_editor", "📝 Texteditor",
            lambda checked: self._toggle_panel("text_editor", checked), enabled=True)
        self.toolbar.add_panel_button("student_list", "📋 Schülerliste",
            lambda checked: self._toggle_panel("student_list", checked), enabled=True)
        self.toolbar.add_class_selector_button(self._show_class_menu)
        self.toolbar.add_separator()
        self.toolbar.add_panel_button("timer", "⏱ Timer",
            lambda checked: self._toggle_panel("timer", checked), enabled=True)
        self.toolbar.add_panel_button("random_name", "🎲 Zufall",
            lambda checked: self._toggle_panel("random_name", checked), enabled=True)
        self.toolbar.add_panel_button("traffic_light", "🚦 Ampel",
            lambda checked: self._toggle_panel("traffic_light", checked), enabled=True)
        ampel_btn = self.toolbar._panel_buttons["traffic_light"]
        ampel_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        ampel_btn.customContextMenuRequested.connect(self._show_ampel_options)
        self.toolbar.add_panel_button("symbols", "🖼 Symbole",
            lambda checked: self._toggle_panel("symbols", checked), enabled=True)
        self.toolbar.add_panel_button("noise_monitor", "🔊 Lautstärke",
            lambda checked: self._toggle_panel("noise_monitor", checked), enabled=True)
        self.toolbar.add_panel_button("qr_code", "📱 QR-Code",
            lambda checked: self._toggle_panel("qr_code", checked), enabled=True)
        self.toolbar.add_separator()
        self.toolbar.add_panel_button("help", "❓ Hilfe",
            lambda checked: self._toggle_panel("help", checked), enabled=True)
        self.toolbar.add_separator()
        bg_btn = self.toolbar.add_panel_button("white_bg", "⬜ Hintergrund",
            lambda checked: self._toggle_white_bg(checked), enabled=True)
        bg_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        bg_btn.customContextMenuRequested.connect(self._pick_bg_color)
        self.toolbar.set_button_checked("white_bg", False)

        # Drawing button
        self.toolbar.add_panel_button("draw", "✏️ Zeichnen",
            lambda checked: self._toggle_drawing(checked), enabled=True)
        self.toolbar.set_button_checked("draw", False)

        # Cleanup routine button (left-click = show, right-click = edit)
        cleanup_btn = self.toolbar.add_panel_button("cleanup", "🧹 Aufräumen",
            lambda checked: self._toggle_cleanup(checked), enabled=True)
        cleanup_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        cleanup_btn.customContextMenuRequested.connect(self._edit_cleanup_text)
        self.toolbar.set_button_checked("cleanup", False)

        # Pause timer button
        self.toolbar.add_panel_button("pause", "⏸ Pause",
            lambda checked: self._toggle_pause(checked), enabled=True)
        self.toolbar.set_button_checked("pause", False)

        # Smartboard button (move overlay to second screen)
        self.toolbar.add_separator()
        self.toolbar.add_panel_button("smartboard", "🖥 Smartboard",
            lambda checked: self._toggle_smartboard(checked), enabled=True)
        self.toolbar.set_button_checked("smartboard", False)
        self._on_secondary_screen = False

        # Minimize + Quit
        self.toolbar.add_minimize_button(self._minimize_all)
        self.toolbar.add_quit_button(self._quit)

        # White background shortcut
        sc_white = QShortcut(QKeySequence("Ctrl+Shift+W"), self.toolbar)
        sc_white.activated.connect(self._toggle_white_bg_shortcut)

        # ESC in white mode → sync toolbar button
        self.background.esc_white_off.connect(
            lambda: self.toolbar.set_button_checked("white_bg", False))

        # Bernd das Brot Easter Egg (Ctrl+Alt+B)
        self._bernd_player = None
        self._bernd_keys_down = False
        if sys.platform == "win32":
            # Windows: global hotkey via GetAsyncKeyState polling
            self._bernd_timer = QTimer()
            self._bernd_timer.setInterval(500)
            def check_bernd_keys():
                VK_CTRL, VK_ALT, VK_B = 0x11, 0x12, 0x42
                ctrl = ctypes.windll.user32.GetAsyncKeyState(VK_CTRL) & 0x8000
                alt = ctypes.windll.user32.GetAsyncKeyState(VK_ALT) & 0x8000
                b = ctypes.windll.user32.GetAsyncKeyState(VK_B) & 0x8000
                if ctrl and alt and b:
                    if not self._bernd_keys_down:
                        self._bernd_keys_down = True
                        self._play_bernd()
                else:
                    self._bernd_keys_down = False
            self._bernd_timer.timeout.connect(check_bernd_keys)
            self._bernd_timer.start()
        else:
            # Linux: poll X11 keyboard state (works globally, like Windows approach)
            self._bernd_timer = QTimer()
            self._bernd_timer.setInterval(500)
            try:
                import Xlib.display, Xlib.X
                _xdisplay = Xlib.display.Display()
                self._xdisplay = _xdisplay  # prevent GC, closed on exit
                _ctrl_codes = set(_xdisplay.keysym_to_keycodes(0xFFE3))   # Control_L
                _ctrl_codes |= set(_xdisplay.keysym_to_keycodes(0xFFE4)) # Control_R
                _alt_codes = set(_xdisplay.keysym_to_keycodes(0xFFE9))   # Alt_L
                _alt_codes |= set(_xdisplay.keysym_to_keycodes(0xFFEA))  # Alt_R
                _b_codes = set(_xdisplay.keysym_to_keycodes(0x62))       # 'b'
                _b_codes |= set(_xdisplay.keysym_to_keycodes(0x42))      # 'B'

                def check_bernd_x11():
                    keys = _xdisplay.query_keymap()
                    def is_pressed(keycodes):
                        return any(keys[kc // 8] & (1 << (kc % 8)) for kc, _ in keycodes)
                    if is_pressed(_ctrl_codes) and is_pressed(_alt_codes) and is_pressed(_b_codes):
                        if not self._bernd_keys_down:
                            self._bernd_keys_down = True
                            self._play_bernd()
                    else:
                        self._bernd_keys_down = False

                self._bernd_timer.timeout.connect(check_bernd_x11)
                self._bernd_timer.start()
            except Exception:
                pass  # Xlib not available, shortcut won't work

        # Auto-size and center toolbar after all buttons are added
        QTimer.singleShot(0, self._center_toolbar)

        # Connect close signals
        for pid, panel in self._panels.items():
            panel.closed.connect(lambda p=pid: self.toolbar.set_button_checked(p, False))

        # Initially hide most panels
        for pid in ["timer", "random_name", "traffic_light", "symbols", "noise_monitor", "qr_code", "help"]:
            self._panels[pid].hide()
            self.toolbar.set_button_checked(pid, False)

        # Try to restore last session
        self._restore_last_session()

    def _get_students(self):
        return self._loaded_students

    def _open_student_notes(self, student_key):
        if not hasattr(self, '_student_notes_dialogs'):
            self._student_notes_dialogs = {}
        if student_key in self._student_notes_dialogs:
            dlg = self._student_notes_dialogs[student_key]
            if dlg.isVisible():
                dlg.raise_()
                return
        cn = getattr(self, '_loaded_class_name', None) or "default"
        dlg = StudentNotesDialog(student_key, cn)
        dlg.destroyed.connect(lambda: self._student_notes_dialogs.pop(student_key, None))
        dlg.show()
        dlg.raise_()
        self._student_notes_dialogs[student_key] = dlg

    def _get_student_active_notes(self, student_key):
        cn = getattr(self, '_loaded_class_name', None)
        if not cn:
            return []
        notes = load_student_notes(cn)
        return get_active_notes(student_key, notes)

    def _toggle_white_bg(self, checked):
        self.background.set_white_mode(checked)
        if checked:
            # Raise toolbar and all visible panels above the white background
            self.toolbar.raise_()
            for panel in self._panels.values():
                if panel.isVisible():
                    panel.raise_()

    def _toggle_white_bg_shortcut(self):
        new_state = not self.background._white_mode
        self.background.set_white_mode(new_state)
        self.toolbar.set_button_checked("white_bg", new_state)
        if new_state:
            self.toolbar.raise_()
            for panel in self._panels.values():
                if panel.isVisible():
                    panel.raise_()

    # Soft preset colors for background picker
    BG_PRESETS = [
        QColor("#FFFFFF"),     # Weiß
        QColor("#F5F0E8"),     # Warmweiß / Creme
        QColor("#E8F0E8"),     # Mintgrün
        QColor("#E0EAF5"),     # Himmelblau
        QColor("#F5E8F0"),     # Rosé
        QColor("#F5F2E0"),     # Sandgelb
        QColor("#EAE0F5"),     # Flieder
        QColor("#E0F5F0"),     # Aqua
        QColor("#F0EDE5"),     # Beige
        QColor("#D8E8D8"),     # Salbeigrün
        QColor("#D5DEE8"),     # Taubenblau
        QColor("#F0E0D0"),     # Pfirsich
        QColor("#E8E0D0"),     # Leinen
        QColor("#D0D8E0"),     # Silberblau
        QColor("#E5D8C8"),     # Cappuccino
        QColor("#D8E0C8"),     # Pistazie
    ]

    def _pick_bg_color(self, _pos):
        dlg = QColorDialog(self.background._bg_color, self.toolbar)
        # Add soft presets as custom colors
        for i, c in enumerate(self.BG_PRESETS):
            QColorDialog.setCustomColor(i, c)
        if dlg.exec():
            color = dlg.selectedColor()
            self.background.set_bg_color(color)
            save_app_settings(bg_color=color)
            # Auto-activate if not already on
            if not self.background._white_mode:
                self.background.set_white_mode(True)
                self.toolbar.set_button_checked("white_bg", True)
                self.toolbar.raise_()
                for panel in self._panels.values():
                    if panel.isVisible():
                        panel.raise_()

    def _play_bernd(self):
        """Play Bernd das Brot 'Mist!' easter egg with transparent background."""
        sounds = get_sounds_dir()

        # Look for pre-processed alpha frames
        alpha_dir = os.path.join(sounds, "_alpha_frames")
        # Prefer wav (universal support) over m4a
        audio_file = os.path.join(sounds, "bernd_mist_audio.wav")
        if not os.path.exists(audio_file):
            audio_file = os.path.join(sounds, "bernd_mist_audio.m4a")
        has_frames = os.path.isdir(alpha_dir) and os.path.exists(audio_file)

        if not has_frames:
            # Fallback: just play audio from any bernd file
            for ext in (".wav", ".mp3", ".mp4"):
                path = os.path.join(sounds, f"bernd_mist{ext}")
                if os.path.exists(path):
                    if sys.platform == "linux":
                        for cmd in (["paplay", path], ["aplay", path],
                                    ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", path]):
                            if shutil.which(cmd[0]):
                                proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                                self._bernd_player = type('', (), {'_proc': proc})()
                                return
                    elif HAS_MULTIMEDIA:
                        player = QMediaPlayer(self.toolbar)
                        audio_out = QAudioOutput(self.toolbar)
                        audio_out.setVolume(1.0)
                        player.setAudioOutput(audio_out)
                        player.setSource(QUrl.fromLocalFile(path))
                        player.play()
                        self._bernd_player = type('', (), {'_player': player, '_audio': audio_out})()
                        return
            return

        # Close previous popup
        if self._bernd_player and hasattr(self._bernd_player, '_win'):
            try:
                self._bernd_player._win.close()
            except Exception:
                pass

        # Load all frames as QPixmap
        frame_files = sorted(glob.glob(os.path.join(alpha_dir, "frame_*.png")))
        if not frame_files:
            return
        frames = [QPixmap(f) for f in frame_files]

        # Create transparent window with QLabel
        win = QWidget()
        win.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        win.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        fw, fh = frames[0].width(), frames[0].height()
        screen = QApplication.primaryScreen().geometry()
        win.setFixedSize(fw, fh)
        win.move(screen.width() // 2 - fw // 2, screen.height() // 2 - fh // 2)

        lbl = QLabel(win)
        lbl.setStyleSheet("background: transparent;")
        lbl.setGeometry(0, 0, fw, fh)
        lbl.setPixmap(frames[0])

        # Frame timer — sync to audio playback position
        duration_ms = 4440  # video duration in ms
        frame_state = {"start_time": 0}
        frame_timer = QTimer(win)
        frame_timer.setInterval(30)

        def cleanup_bernd():
            frame_timer.stop()
            # Kill audio subprocess if still running
            bp = self._bernd_player
            if bp and getattr(bp, '_audio_proc', None):
                try:
                    bp._audio_proc.terminate()
                except Exception:
                    pass
            win.close()
            self._bernd_player = None  # Free all frames + pixmaps

        def next_frame():
            elapsed = time.monotonic() * 1000 - frame_state["start_time"]
            idx = int(elapsed / duration_ms * len(frames))
            if idx >= len(frames):
                cleanup_bernd()
                return
            lbl.setPixmap(frames[idx])

        frame_timer.timeout.connect(next_frame)

        # Play audio
        audio_proc = None
        if sys.platform == "linux":
            for cmd in (["paplay", audio_file], ["aplay", audio_file],
                        ["ffplay", "-nodisp", "-autoexit", "-loglevel", "quiet", audio_file]):
                if shutil.which(cmd[0]):
                    audio_proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    break
        elif sys.platform == "win32" and audio_file.endswith(".wav"):
            # winsound is reliable on Windows for wav files
            try:
                import winsound
                winsound.PlaySound(audio_file, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass
        elif HAS_MULTIMEDIA:
            _player = QMediaPlayer(win)
            _audio_out = QAudioOutput(win)
            _audio_out.setVolume(1.0)
            _player.setAudioOutput(_audio_out)
            _player.setSource(QUrl.fromLocalFile(audio_file))
            _player.play()

        win.show()
        frame_state["start_time"] = time.monotonic() * 1000
        frame_timer.start()

        self._bernd_player = type('', (), {
            '_win': win, '_timer': frame_timer,
            '_audio_proc': audio_proc, '_frames': frames,
            '_qt_player': locals().get('_player'),
            '_qt_audio': locals().get('_audio_out'),
        })()

    def _toggle_smartboard(self, checked):
        screens = QApplication.screens()
        if checked:
            if len(screens) < 2:
                # Try to extend display first
                if sys.platform == "win32":
                    subprocess.Popen(["DisplaySwitch.exe", "/extend"],
                                     creationflags=subprocess.CREATE_NO_WINDOW)
                    # Wait for display to settle, then move
                    QTimer.singleShot(3000, self._move_to_secondary)
                    return
            self._move_to_secondary()
        else:
            self._move_to_primary()

    def _move_to_secondary(self):
        screens = QApplication.screens()
        if len(screens) < 2:
            self.toolbar.set_button_checked("smartboard", False)
            return
        target = screens[1].geometry()
        self._move_overlay_to_screen(target)
        self._on_secondary_screen = True

    def _move_to_primary(self):
        screens = QApplication.screens()
        target = screens[0].geometry()
        self._move_overlay_to_screen(target)
        self._on_secondary_screen = False
        if sys.platform == "win32":
            subprocess.Popen(["DisplaySwitch.exe", "/duplicate"],
                             creationflags=subprocess.CREATE_NO_WINDOW)

    def _move_overlay_to_screen(self, screen_geo):
        """Move all overlay elements to the given screen geometry."""
        sx, sy, sw, sh = screen_geo.x(), screen_geo.y(), screen_geo.width(), screen_geo.height()
        # Move background
        self.background.setGeometry(screen_geo)
        # Move toolbar — center on target screen
        self.toolbar.adjustToContent()
        tw = self.toolbar.width()
        self.toolbar.move(sx + max(0, (sw - tw) // 2), sy + 8)
        # Move restore button
        self.restore_btn.move(sx + sw // 2 - 24, sy + 4)
        # Move all visible panels — shift by screen offset, clamp to target
        for panel in self._panels.values():
            px, py = panel.x(), panel.y()
            pw, ph = panel.width(), panel.height()
            # Clamp to target screen bounds
            px = max(sx, min(px, sx + sw - 100))
            py = max(sy, min(py, sy + sh - 100))
            pw = min(pw, sw)
            ph = min(ph, sh)
            panel.setGeometry(px, py, pw, ph)
        # Move drawing and cleanup overlays to the target screen
        self.drawing_overlay.move_to_screen(screen_geo)
        self.cleanup_overlay.move_to_screen(screen_geo)
        self.pause_overlay.move_to_screen(screen_geo)

    def _toggle_drawing(self, checked):
        if checked:
            self.drawing_overlay.show()
            self.drawing_overlay.raise_()
            self.toolbar.raise_()
        else:
            self.drawing_overlay.hide()

    def _toggle_cleanup(self, checked):
        if checked:
            self.cleanup_overlay.show()
            self.cleanup_overlay.raise_()
            self.toolbar.raise_()
        else:
            self.cleanup_overlay.hide()

    def _toggle_pause(self, checked):
        if checked:
            timer_refs = []
            # Main timer panel
            if hasattr(self.timer_panel, '_timer_qobj'):
                timer_refs.append((self.timer_panel._timer_qobj, self.timer_panel._timer_state))
            # Ampel countdown timer
            if hasattr(self.traffic_panel, '_countdown_timer'):
                timer_refs.append((self.traffic_panel._countdown_timer, None))
            # Position on correct screen
            if self._on_secondary_screen:
                screens = QApplication.screens()
                if len(screens) > 1:
                    self.pause_overlay.move_to_screen(screens[1].geometry())
            else:
                self.pause_overlay.move_to_screen(QApplication.primaryScreen().geometry())
            self.pause_overlay.start_pause(timer_refs)
        else:
            self.pause_overlay._end_pause()

    def _edit_cleanup_text(self, _pos):
        """Open a dialog to edit the cleanup text with formatting."""
        screen = QApplication.primaryScreen().geometry()
        editor = FloatingPanel("Aufräum-Text bearbeiten")
        editor.setGeometry(screen.width() // 2 - 220, screen.height() // 2 - 200, 440, 400)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(8, 8, 8, 8)
        cl.setSpacing(6)

        text_edit = QTextEdit(content)
        text_edit.setStyleSheet(
            f"QTextEdit {{ background-color: rgba(20,20,20,200); color: white; "
            f"border: 1px solid rgba(255,255,255,50); border-radius: 6px; padding: 10px; "
            f"font-size: 14px; }} {SCROLLBAR_STYLE()}"
        )
        text_edit.setAcceptRichText(True)
        text_edit.setHtml(self.cleanup_overlay.get_html())

        fmt_toolbar = FormattingToolbar(text_edit, content)
        cl.addWidget(fmt_toolbar)
        cl.addWidget(text_edit)

        btn_save = QPushButton("Speichern", content)
        btn_save.setStyleSheet(INNER_BUTTON_STYLE())
        def save_and_close():
            self.cleanup_overlay.set_html(text_edit.toHtml())
            fmt_toolbar.stop_all_blinks()
            editor.hide()
            editor.deleteLater()
        btn_save.clicked.connect(save_and_close)
        cl.addWidget(btn_save)

        editor.set_content_widget(content)
        editor.show()
        editor.raise_()

    def _show_ampel_options(self, _pos):
        """Open options dialog for the traffic light counter system."""
        ts = self.traffic_panel.traffic_state
        screen = QApplication.primaryScreen().geometry()
        dialog = FloatingPanel("🚦 Ampel-Optionen")
        dialog.setGeometry(screen.width() // 2 - 190, screen.height() // 2 - 180, 380, 360)

        content = QWidget()
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 12, 12, 12)
        cl.setSpacing(10)

        spin_style = (
            "QSpinBox { background: rgba(40,40,40,200); color: white; "
            "border: 1px solid rgba(255,255,255,50); border-radius: 4px; padding: 4px; font-size: 13px; }"
        )
        lbl_style = "color: white; font-size: 13px; background: transparent; border: none;"

        # Enable checkbox — large, prominent with colored indicator
        chk_enabled = QCheckBox(" Zähler aktivieren", content)
        chk_enabled.setChecked(ts.get("counter_enabled", False))
        chk_enabled.setStyleSheet(
            "QCheckBox { color: white; font-size: 15px; font-weight: bold; "
            "  background: transparent; border: none; spacing: 8px; }"
            "QCheckBox::indicator { width: 22px; height: 22px; border-radius: 4px; "
            "  border: 2px solid rgba(255,255,255,120); background: rgba(40,40,40,200); }"
            "QCheckBox::indicator:checked { background: #44BB44; "
            "  border: 2px solid #44DD44; }"
            "QCheckBox::indicator:unchecked { background: rgba(60,60,60,200); "
            "  border: 2px solid rgba(255,255,255,60); }"
        )
        cl.addWidget(chk_enabled)

        # Threshold spinboxes
        row1 = QHBoxLayout()
        lbl1 = QLabel("Klicks bis Gelb:", content)
        lbl1.setStyleSheet(lbl_style)
        spin_to_yellow = QSpinBox(content)
        spin_to_yellow.setRange(1, 20)
        spin_to_yellow.setValue(ts.get("counter_to_yellow", 3))
        spin_to_yellow.setStyleSheet(spin_style)
        row1.addWidget(lbl1)
        row1.addWidget(spin_to_yellow)
        cl.addLayout(row1)

        row2 = QHBoxLayout()
        lbl2 = QLabel("Klicks bis Rot:", content)
        lbl2.setStyleSheet(lbl_style)
        spin_to_red = QSpinBox(content)
        spin_to_red.setRange(1, 20)
        spin_to_red.setValue(ts.get("counter_to_red", 3))
        spin_to_red.setStyleSheet(spin_style)
        row2.addWidget(lbl2)
        row2.addWidget(spin_to_red)
        cl.addLayout(row2)

        # Separator
        sep = QFrame(content)
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color: rgba(255,255,255,40);")
        cl.addWidget(sep)

        # Countdown — integer minutes (0 = disabled)
        def _make_min_spin(parent, secs_value):
            spin = QSpinBox(parent)
            spin.setRange(0, 60)
            spin.setSpecialValueText("Aus")
            spin.setStyleSheet(spin_style)
            spin.setSuffix(" min")
            spin.setValue(secs_value // 60 if secs_value > 0 else 0)
            return spin

        row3 = QHBoxLayout()
        lbl3 = QLabel("Gelb-Countdown:", content)
        lbl3.setStyleSheet(lbl_style)
        spin_yellow_cd = _make_min_spin(content, ts.get("yellow_countdown_secs", 0))
        row3.addWidget(lbl3)
        row3.addWidget(spin_yellow_cd)
        cl.addLayout(row3)

        row4 = QHBoxLayout()
        lbl4 = QLabel("Rot-Countdown:", content)
        lbl4.setStyleSheet(lbl_style)
        spin_red_cd = _make_min_spin(content, ts.get("red_countdown_secs", 0))
        row4.addWidget(lbl4)
        row4.addWidget(spin_red_cd)
        cl.addLayout(row4)

        cl.addStretch()

        btn_apply = QPushButton("Übernehmen", content)
        btn_apply.setStyleSheet(INNER_BUTTON_STYLE())
        def apply_and_close():
            ts["counter_enabled"] = chk_enabled.isChecked()
            ts["counter_to_yellow"] = spin_to_yellow.value()
            ts["counter_to_red"] = spin_to_red.value()
            # Convert minutes back to seconds
            ts["yellow_countdown_secs"] = spin_yellow_cd.value() * 60
            ts["red_countdown_secs"] = spin_red_cd.value() * 60
            dialog.hide()
            dialog.deleteLater()
        btn_apply.clicked.connect(apply_and_close)
        cl.addWidget(btn_apply)

        dialog.set_content_widget(content)
        dialog.show()
        dialog.raise_()

    def _toggle_panel(self, panel_id, checked):
        panel = self._panels.get(panel_id)
        if panel:
            if checked:
                panel.show()
                panel.raise_()
            else:
                panel.hide()

    def _show_class_menu(self):
        menu = QMenu()
        menu_style = """
            QMenu { background-color: rgba(40,40,40,245); color: white; border: 1px solid rgba(255,255,255,80); border-radius: 6px; padding: 4px; font-size: 14px; }
            QMenu::item { padding: 8px 24px; border-radius: 4px; }
            QMenu::item:selected { background-color: rgba(0,120,215,200); }
        """
        menu.setStyleSheet(menu_style)
        class_files = discover_class_files()
        if not class_files:
            a = menu.addAction("Keine Klassen gefunden")
            a.setEnabled(False)
        else:
            for dn, fp in class_files:
                a = menu.addAction(dn)
                a.triggered.connect(lambda checked, f=fp: self._load_class(f))

        menu.addSeparator()

        # Create new class
        a_new = menu.addAction("➕ Neue Klasse erstellen…")
        a_new.triggered.connect(lambda: self._open_class_editor())

        # Edit existing class
        if class_files:
            edit_menu = menu.addMenu("✏️ Klasse bearbeiten…")
            edit_menu.setStyleSheet(menu_style)
            for dn, fp in class_files:
                a = edit_menu.addAction(dn)
                a.triggered.connect(lambda checked, f=fp: self._open_class_editor(f))

            # Delete existing class
            del_menu = menu.addMenu("🗑 Klasse löschen…")
            del_menu.setStyleSheet(menu_style)
            for dn, fp in class_files:
                a = del_menu.addAction(dn)
                a.triggered.connect(lambda checked, f=fp: self._delete_class(f))

        btn = self.toolbar._panel_buttons.get("class_selector")
        if btn:
            menu.exec(btn.mapToGlobal(btn.rect().bottomLeft()))

    def _load_class(self, filepath):
        try:
            # Save current layout before switching
            if self._loaded_class_name:
                self._save_current_layout()

            cn, students = load_class_list(filepath)
            self._loaded_students = (cn, students)
            self._loaded_class_name = cn
            self._loaded_class_filepath = filepath
            load_students_into_panel(self.student_panel, cn, students,
                                     open_notes_fn=self._open_student_notes)
            if hasattr(self.traffic_panel, 'load_students'):
                self.traffic_panel.load_students(students)
            # Cleanup expired notes on class load
            notes = load_student_notes(cn)
            if notes:
                cleanup_expired_notes(notes)
                save_student_notes(cn, notes)
            if not self.student_panel.isVisible():
                self.student_panel.show()
                self.toolbar.set_button_checked("student_list", True)

            # Try to load layout for this class
            layout_data = load_layout(cn)
            if layout_data:
                self._apply_layout(layout_data)

        except Exception as e:
            print(f"Error loading class: {e}")

    def _open_class_editor(self, filepath=None):
        """Open the class editor panel for creating or editing a class."""
        class_name = ""
        students = None
        edit_fp = None

        if filepath:
            try:
                cn, studs = load_class_list(filepath)
                class_name = cn
                students = studs
                edit_fp = filepath
            except Exception as e:
                print(f"Error loading class for editing: {e}")
                return

        screen = QApplication.primaryScreen().geometry()
        editor = create_class_editor_panel(self._load_class, class_name, students, edit_fp)
        editor.setGeometry(screen.width() // 2 - S(220), screen.height() // 2 - S(250), S(440), S(500))
        editor.show()
        editor.raise_()

    def _delete_class(self, filepath):
        """Delete a class after confirmation."""
        try:
            cn, _ = load_class_list(filepath)
        except Exception:
            cn = os.path.basename(filepath)

        msg = QMessageBox()
        msg.setWindowTitle("Klasse löschen")
        msg.setText(f"Klasse '{cn}' wirklich löschen?")
        msg.setInformativeText("Diese Aktion kann nicht rückgängig gemacht werden.")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        msg.setStyleSheet(
            "QMessageBox { background: rgba(40,40,40,245); color: white; }"
            "QPushButton { background: rgba(60,60,60,200); color: white; border: 1px solid rgba(255,255,255,60); "
            "border-radius: 4px; padding: 6px 16px; font-size: 13px; }"
            "QPushButton:hover { background: rgba(80,80,80,220); }"
        )

        if msg.exec() != QMessageBox.StandardButton.Yes:
            return

        # Delete class file
        try:
            os.remove(filepath)
        except Exception as e:
            print(f"Error deleting class file: {e}")

        # Delete corresponding layout file
        layout_path = get_layout_filepath(cn)
        if os.path.exists(layout_path):
            try:
                os.remove(layout_path)
            except Exception:
                pass

        # If deleted class was currently loaded, clear state
        if self._loaded_class_name == cn:
            self._loaded_students = None
            self._loaded_class_name = None
            self._loaded_class_filepath = None
            # Clear student panel
            layout = self.student_panel.student_layout
            while layout.count() > 1:
                item = layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()
            self.student_panel.header_label.setText("📋 Schülerliste")
            self.student_panel.set_title("📋 Schülerliste")
            # Clear traffic light
            if hasattr(self.traffic_panel, 'traffic_state'):
                self.traffic_panel.traffic_state["students"] = []
                self.traffic_panel.traffic_state["lights"] = {}
                self.traffic_panel.load_students([])

    def _save_current_layout(self):
        """Save the current layout state."""
        text_html = ""
        if hasattr(self.text_panel, 'text_edit'):
            text_html = self.text_panel.text_edit.toHtml()

        traffic_lights = {}
        if hasattr(self.traffic_panel, 'traffic_state'):
            traffic_lights = dict(self.traffic_panel.traffic_state.get("lights", {}))

        ampel_rules = {}
        if hasattr(self.traffic_panel, 'rules_green'):
            ampel_rules = {
                "green": self.traffic_panel.rules_green.toPlainText(),
                "yellow": self.traffic_panel.rules_yellow.toPlainText(),
                "red": self.traffic_panel.rules_red.toPlainText(),
            }

        noise_thresholds = None
        if hasattr(self.noise_panel, 'noise_spin_yellow'):
            noise_thresholds = {
                "yellow": self.noise_panel.noise_spin_yellow.value(),
                "red": self.noise_panel.noise_spin_red.value(),
            }

        ampel_counter_settings = None
        if hasattr(self.traffic_panel, 'traffic_state'):
            ts = self.traffic_panel.traffic_state
            ampel_counter_settings = {
                "counter_enabled": ts.get("counter_enabled", False),
                "counter_to_yellow": ts.get("counter_to_yellow", 3),
                "counter_to_red": ts.get("counter_to_red", 3),
                "yellow_countdown_secs": ts.get("yellow_countdown_secs", 0),
                "red_countdown_secs": ts.get("red_countdown_secs", 0),
            }

        save_layout(
            self._panels,
            self.toolbar,
            text_html,
            traffic_lights,
            self._loaded_class_name,
            ampel_rules,
            noise_thresholds,
            ampel_counter_settings,
        )

    def _apply_layout(self, data):
        """Apply a saved layout."""
        # Toolbar position — auto-size and center
        screen = QApplication.primaryScreen().geometry()
        self._center_toolbar()

        # Panels — clamp to current screen so nothing is off-screen
        panels_data = data.get("panels", {})
        for pid, pdata in panels_data.items():
            panel = self._panels.get(pid)
            if panel:
                px = pdata.get("x", panel.x())
                py = pdata.get("y", panel.y())
                pw = pdata.get("width", panel.width())
                ph = pdata.get("height", panel.height())
                # Clamp size to screen
                pw = min(pw, screen.width())
                ph = min(ph, screen.height())
                # Ensure at least 100px of the panel is visible on screen
                px = max(0, min(px, screen.width() - 100))
                py = max(0, min(py, screen.height() - 100))
                panel.setGeometry(px, py, pw, ph)
                visible = pdata.get("visible", False)
                if visible:
                    panel.show()
                    panel.raise_()
                else:
                    panel.hide()
                self.toolbar.set_button_checked(pid, visible)

                if pdata.get("minimized", False) and not panel._is_minimized:
                    panel.toggle_minimize()

        # Text content
        text_html = data.get("text_content", "")
        if text_html and hasattr(self.text_panel, 'text_edit'):
            self.text_panel.text_edit.setHtml(text_html)

        # Traffic lights
        traffic_lights = data.get("traffic_lights", {})
        if traffic_lights and hasattr(self.traffic_panel, 'traffic_state'):
            self.traffic_panel.traffic_state["lights"].update(traffic_lights)
            # Refresh display if students are loaded
            if self.traffic_panel.traffic_state["students"]:
                if self.traffic_panel.traffic_state["mode"] == "click":
                    # Trigger a refresh by re-loading students
                    self.traffic_panel.load_students(self.traffic_panel.traffic_state["students"])

        # Ampel rules
        ampel_rules = data.get("ampel_rules", {})
        if isinstance(ampel_rules, dict) and hasattr(self.traffic_panel, 'rules_green'):
            self.traffic_panel.rules_green.setPlainText(ampel_rules.get("green", ""))
            self.traffic_panel.rules_yellow.setPlainText(ampel_rules.get("yellow", ""))
            self.traffic_panel.rules_red.setPlainText(ampel_rules.get("red", ""))

        # Noise thresholds
        noise_thresholds = data.get("noise_thresholds", {})
        if noise_thresholds:
            if hasattr(self.noise_panel, 'noise_spin_yellow'):
                self.noise_panel.noise_spin_yellow.setValue(noise_thresholds.get("yellow", 5))
            if hasattr(self.noise_panel, 'noise_spin_red'):
                self.noise_panel.noise_spin_red.setValue(noise_thresholds.get("red", 10))

        # Ampel counter settings
        counter_settings = data.get("ampel_counter_settings", {})
        if counter_settings and hasattr(self.traffic_panel, 'traffic_state'):
            ts = self.traffic_panel.traffic_state
            ts["counter_enabled"] = counter_settings.get("counter_enabled", False)
            ts["counter_to_yellow"] = counter_settings.get("counter_to_yellow", 3)
            ts["counter_to_red"] = counter_settings.get("counter_to_red", 3)
            ts["yellow_countdown_secs"] = counter_settings.get("yellow_countdown_secs", 0)
            ts["red_countdown_secs"] = counter_settings.get("red_countdown_secs", 0)

    def _restore_last_session(self):
        """Restore the last session on startup."""
        last_class = load_last_session_class()

        if last_class:
            # Find the class file
            class_files = discover_class_files()
            for dn, fp in class_files:
                try:
                    cn, students = load_class_list(fp)
                    if cn == last_class:
                        self._loaded_students = (cn, students)
                        self._loaded_class_name = cn
                        self._loaded_class_filepath = fp
                        load_students_into_panel(self.student_panel, cn, students,
                                                 open_notes_fn=self._open_student_notes)
                        if hasattr(self.traffic_panel, 'load_students'):
                            self.traffic_panel.load_students(students)
                        break
                except Exception:
                    pass

        # Load layout (class-specific or default)
        layout_data = load_layout(last_class)
        if layout_data:
            self._apply_layout(layout_data)

    def _center_toolbar(self):
        """Auto-size toolbar to content and center on current screen."""
        self.toolbar.adjustToContent()
        screens = QApplication.screens()
        if self._on_secondary_screen and len(screens) >= 2:
            screen = screens[1].geometry()
        else:
            screen = screens[0].geometry()
        tw = self.toolbar.width()
        tx = screen.x() + max(0, (screen.width() - tw) // 2)
        self.toolbar.move(tx, screen.y() + 8)

    def _minimize_all(self):
        self._visible_before_minimize = []
        for pid, panel in self._panels.items():
            if panel.isVisible():
                self._visible_before_minimize.append(pid)
                panel.hide()
        self.toolbar.hide()
        self.restore_btn.show()
        self.restore_btn.raise_()

    def _restore_all(self):
        self.restore_btn.hide()
        # If toolbar was just collapsed (not full minimize), re-show it
        if not self.toolbar.isVisible() and not self._visible_before_minimize:
            self.toolbar.show()
            self.toolbar.raise_()
            self._center_toolbar()
            return
        # Otherwise restore everything from full minimize
        self.toolbar.show()
        self.toolbar.raise_()
        for pid in self._visible_before_minimize:
            panel = self._panels.get(pid)
            if panel:
                panel.show()
                panel.raise_()
                self.toolbar.set_button_checked(pid, True)
        self._visible_before_minimize = []
        self._center_toolbar()

    def _quit(self):
        """Save layout and quit."""
        self._save_current_layout()
        # Clean up X11 display connection if open
        if hasattr(self, '_xdisplay') and self._xdisplay:
            try:
                self._xdisplay.close()
            except Exception:
                pass
        # Kill any running bernd audio subprocess
        if self._bernd_player and getattr(self._bernd_player, '_audio_proc', None):
            try:
                self._bernd_player._audio_proc.terminate()
            except Exception:
                pass
        self.app.quit()

    def show(self):
        self.background.show()
        self.toolbar.show()
        self.text_panel.show()
        self.student_panel.show()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)

    # Ensure emoji rendering works on Linux by loading a bundled CBDT emoji font
    # (Qt cannot render the COLRv1 format that modern distros ship)
    if sys.platform != "win32":
        bundled_emoji = os.path.join(os.path.dirname(os.path.abspath(__file__)), "NotoColorEmoji.ttf")
        if os.path.isfile(bundled_emoji):
            font_id = QFontDatabase.addApplicationFont(bundled_emoji)
            if font_id >= 0:
                loaded = QFontDatabase.applicationFontFamilies(font_id)
                if loaded:
                    font = app.font()
                    families = font.families() if hasattr(font, 'families') else [font.family()]
                    for fam in loaded:
                        if fam not in families:
                            families.append(fam)
                    font.setFamilies(families)
                    app.setFont(font)

    global SCALE_FACTOR
    SCALE_FACTOR = compute_scale_factor()

    overlay = OverlayApp()
    overlay.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
