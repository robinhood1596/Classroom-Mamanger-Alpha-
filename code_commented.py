"""
Classroom Overlay Tool
======================
A transparent, always-on-top desktop overlay window built with PyQt6.

WHAT IS THIS FILE?
This is a complete desktop application for teachers. It creates a transparent
overlay on your screen with floating panels for a timer, traffic light system,
work symbols, and more.

HOW PYTHON FILES WORK:
- Python reads this file from top to bottom
- Lines starting with # are "comments" — Python ignores them. They're notes for humans.
- Text between triple quotes (like this block) is a "docstring" — also a comment.
- "import" loads code from other files/libraries so we can use it.
- "def" defines a function (a reusable block of code).
- "class" defines a class (a blueprint for creating objects — explained later).

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

# =====================================================================
# IMPORTS
# =====================================================================
# "import" loads code from other files so we can use their functions.
#
# WHAT IS A MODULE / LIBRARY?
# A module is just a Python file with useful functions inside. A library
# is a collection of modules. Python has many built-in ones (the "standard
# library"), and you can install extra ones with "pip install <name>".
#
# WHY DO WE IMPORT?
# Instead of writing everything from scratch, we reuse code others wrote.
# For example, "import json" gives us functions to read/write JSON files.

# --- Standard library imports (built into Python, no installation needed) ---

import sys          # sys.argv = command-line arguments; sys.exit() = quit the program
import os           # File/folder operations: check if files exist, join paths, etc.
import json         # Read/write JSON files (a common format for storing structured data)
import glob         # Find files matching a pattern like "classes/*.json"
import math         # Math functions like math.ceil() (round a number UP)
import random       # Generate random numbers / pick random items from a list
import shutil       # High-level file operations like copying a file to another folder
import struct       # Convert between Python values and raw bytes (used for audio data)

# =====================================================================
# PyQt6 IMPORTS
# =====================================================================
# PyQt6 is a Python wrapper around the Qt GUI framework. It lets you build
# desktop applications with windows, buttons, text fields, layouts, etc.
#
# Think of it like this:
#   - A "widget" is any visible UI element (button, label, text box…)
#   - A "layout" arranges widgets inside a container (horizontal, vertical, grid)
#   - A "signal" is an event that a widget emits (e.g. "button was clicked")
#   - A "slot" is a function that runs when a signal fires
#   - "Stylesheets" are CSS-like strings that control appearance (colors, borders…)
#
# The imports are split into three sub-modules:
#   QtWidgets – visible UI elements (buttons, labels, text boxes, layouts, dialogs)
#   QtCore    – non-visual fundamentals (timers, geometry, signals, data types)
#   QtGui     – drawing, colors, fonts, keyboard shortcuts, images

# "from X import Y" means: from the module X, bring in the specific thing Y.
# This is different from "import X" which imports the whole module.
# Example: "from math import sqrt" lets you write sqrt(4) instead of math.sqrt(4).

from PyQt6.QtWidgets import (
    QApplication,       # The application object – every Qt app needs exactly one
    QWidget,            # Base class for ALL visible UI elements ("widgets")
    QPushButton,        # A clickable button
    QLabel,             # A text or image display (read-only)
    QTextEdit,          # A multi-line rich text editor (supports bold, colors, etc.)
    QComboBox,          # A dropdown / select box
    QHBoxLayout,        # Lays out children left-to-right (horizontal)
    QVBoxLayout,        # Lays out children top-to-bottom (vertical)
    QScrollArea,        # Makes content scrollable if it overflows
    QFrame,             # A basic frame widget, often used as a visual separator line
    QColorDialog,       # Built-in color picker popup
    QMenu,              # Right-click context menu or dropdown menu
    QSpinBox,           # Number input with +/- arrows (e.g. for timer minutes)
    QGridLayout,        # Arranges widgets in rows and columns (like a table)
    QSlider,            # A draggable slider (e.g. for volume)
    QProgressBar,       # A progress bar
    QMessageBox,        # A popup dialog for messages / yes-no questions
    QLineEdit,          # A single-line text input field
    QSizePolicy,        # Controls how a widget grows/shrinks when the window resizes
    QFileDialog,        # A file-open / file-save dialog
    QInputDialog,       # Simple popup to ask for one value (text, number, etc.)
)

from PyQt6.QtCore import (
    Qt,                 # Namespace for constants: alignment, mouse buttons, keys, etc.
    QTimer,             # Calls a function after a delay or at regular intervals
    QPoint,             # A 2D point (x, y) – used for positions
    QRect,              # A rectangle defined by (x, y, width, height)
    QSize,              # A size defined by (width, height)
    pyqtSignal,         # Lets you define custom events that other code can listen to
    QMimeData,          # Carries data during drag-and-drop operations
    QByteArray,         # A raw byte array, used internally by Qt
)

from PyQt6.QtGui import (
    QPainter,           # Low-level 2D drawing: lines, circles, text, images
    QColor,             # A color with red, green, blue, alpha (transparency)
    QKeySequence,       # A keyboard shortcut like "Ctrl+B"
    QShortcut,          # Connects a QKeySequence to a Python function
    QTextCharFormat,    # Text formatting: bold, italic, underline, color, font
    QFont,              # A font definition: family name, point size, weight
    QFontMetrics,       # Measures how wide/tall text would be in a given font
    QIcon,              # An icon image for buttons or window title bars
    QTextCursor,        # The blinking cursor / selection inside a QTextEdit
    QDrag,              # Starts and manages a drag-and-drop operation
    QPen,               # How outlines are drawn: color, width, dash style
    QBrush,             # How areas are filled: solid color, gradient, pattern
    QPixmap,            # An image optimized for fast on-screen drawing
    QImage,             # An image you can inspect/modify pixel by pixel
)

# --- Optional dependencies ---
# These libraries are NOT required. We use "try / except" to handle the case
# where they're not installed.
#
# WHAT IS try / except?
# Sometimes code might fail (e.g., importing a library that isn't installed).
# "try" says "try to run this code". If it fails with a specific error,
# "except" catches that error and runs alternative code instead of crashing.
#
# Example:
#   try:
#       result = 10 / 0          # This will fail (can't divide by zero)
#   except ZeroDivisionError:
#       result = 0               # Use 0 as a fallback instead of crashing

# QtMultimedia provides access to the microphone for the noise monitor.
# If not installed, we just set HAS_MULTIMEDIA = False and skip that feature.
try:
    from PyQt6.QtMultimedia import QAudioSource, QMediaDevices, QAudioFormat
    HAS_MULTIMEDIA = True      # Import succeeded → microphone features available
except ImportError:
    HAS_MULTIMEDIA = False     # Import failed → skip microphone features

# The 'qrcode' library generates QR code images. Same try/except pattern.
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False


# =====================================================================
# HELPER FUNCTIONS
# =====================================================================
# Small utility functions used throughout the app.
#
# WHAT IS A FUNCTION?
# A function is a reusable block of code. You define it with "def":
#   def greet(name):
#       return f"Hello, {name}!"
#
# Then you can call it:  greet("Robin")  →  "Hello, Robin!"
#
# Functions can:
#   - Take "parameters" (inputs) in parentheses
#   - "return" a value back to whoever called them
#   - Have a "docstring" (text in triple quotes) explaining what they do

def get_classes_dir():
    """Return the path to the 'classes' folder next to this script."""
    # __file__ is a special Python variable that contains the path to THIS file.
    # os.path.abspath() makes it a full/absolute path (e.g. C:\Users\robin\overlay\overlay.py)
    # os.path.dirname() gets just the folder part (e.g. C:\Users\robin\overlay\)
    # os.path.join() combines folder + filename with the correct slash for your OS
    # Result: something like "C:\Users\robin\overlay\classes"
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "classes")


def get_layouts_dir():
    """Return the path to the 'layouts' folder next to this script."""
    d = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layouts")
    # os.makedirs creates the folder. exist_ok=True means "don't crash if it
    # already exists" — without this, creating an existing folder would error.
    os.makedirs(d, exist_ok=True)
    return d


def load_class_list(filepath):
    """Load a class JSON file and return (class_name, list_of_students).

    WHAT IS JSON?
    JSON is a text format for storing structured data. It looks like this:
        {"class_name": "5a", "students": ["Anna", "Ben", "Clara"]}
    json.load() reads a JSON file and converts it into Python dictionaries/lists.

    WHAT IS A TUPLE?
    This function returns TWO values: (class_name, students). That's a "tuple" —
    a fixed group of values. The caller can unpack them:
        name, kids = load_class_list("5a.json")
    """
    # "with open(...) as f" opens a file and automatically closes it when done.
    # "r" = read mode, encoding="utf-8" = support special characters (ä, ö, ü…)
    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)     # Parse the JSON file into a Python dictionary
    # dict.get(key, default) returns the value for 'key', or 'default' if missing.
    # This is safer than data["class_name"] which would crash if the key is missing.
    class_name = data.get("class_name", "Unknown")
    students = data.get("students", [])     # [] = empty list as default
    return class_name, students


def discover_class_files():
    """Return a list of (display_name, filepath) for all class JSON files.

    WHAT IS A LIST?
    A list is an ordered collection: ["apple", "banana", "cherry"]
    You can loop over it, add items, remove items, etc.

    WHAT IS A TUPLE IN A LIST?
    This returns a list of tuples: [("Klasse 5a", "path/to/5a.json"), ...]
    Each tuple pairs a display name with its file path.
    """
    classes_dir = get_classes_dir()
    # glob.glob finds all files matching a pattern. "*.json" means any .json file.
    pattern = os.path.join(classes_dir, "*.json")
    files = sorted(glob.glob(pattern))  # sorted() puts them in alphabetical order
    result = []     # Start with an empty list
    for fp in files:
        # "for X in Y" loops through each item in Y, calling it X each time
        try:
            name, _ = load_class_list(fp)
            # _ means "I don't need this value" (the student list)
            # f"..." is an f-string: lets you put variables inside a string
            # f"Klasse {name}" with name="5a" → "Klasse 5a"
            result.append((f"Klasse {name}", fp))
            # .append() adds one item to the end of a list
        except (json.JSONDecodeError, KeyError):
            # If the JSON file is broken/invalid, use the filename instead
            basename = os.path.basename(fp)  # "5a.json" from "C:\...\5a.json"
            result.append((basename, fp))
    return result


def clear_layout(layout):
    """Removes all widgets from a layout, detaching them from their parent.

    WHAT IS A LAYOUT?
    In Qt, a layout automatically arranges widgets (buttons, labels, etc.)
    inside a container. QVBoxLayout stacks them vertically, QHBoxLayout
    horizontally. When you want to replace the contents, you first need
    to remove all existing widgets — that's what this function does.
    """
    # layout.count() returns how many items are in the layout.
    # We keep removing the first item until the layout is empty.
    while layout.count():
        item = layout.takeAt(0)     # Remove and return the first item
        widget = item.widget()      # Get the actual widget from the layout item
        if widget:
            widget.setParent(None)  # Detach from parent → widget gets cleaned up


# =====================================================================
# SHARED STYLESHEET CONSTANTS
# =====================================================================
# WHAT IS A VARIABLE?
# A variable is a name that stores a value. Think of it as a labeled box:
#   CARD_BG = "rgba(30, 30, 30, 220)"
# Now 'CARD_BG' holds that text. Anywhere we write CARD_BG, Python replaces
# it with "rgba(30, 30, 30, 220)". This avoids repeating the same value.
# Variables in ALL_CAPS are "constants" — values we set once and never change.
#
# WHAT IS A STRING?
# A string is text enclosed in quotes: "hello" or 'hello' or """hello""".
# Triple quotes (""") can span multiple lines, which is useful for long text.
#
# WHAT ARE STYLESHEETS?
# Qt supports "stylesheets" – strings that look like CSS (web styling).
# They control colors, borders, rounded corners, padding, fonts, etc.
# You apply them to a widget with: widget.setStyleSheet("...")
#
# The color format "rgba(R, G, B, A)" means:
#   R = red (0-255), G = green (0-255), B = blue (0-255)
#   A = alpha/opacity (0 = fully invisible, 255 = fully solid/opaque)

CARD_BG = "rgba(30, 30, 30, 220)"       # Dark, slightly transparent background
CARD_BORDER = "rgba(255, 255, 255, 60)"  # Faint white border

# Style for buttons in the main toolbar at the top of the screen.
# "QPushButton" targets all QPushButton widgets that use this style.
# ":hover" means when the mouse is over the button, ":pressed" when clicked,
# ":checked" when toggled on, ":disabled" when the button is grayed out.
TOOLBAR_BUTTON_STYLE = """
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

# Style for smaller formatting/mode buttons inside panels.
FORMAT_BUTTON_STYLE = """
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

# Style for the tiny color-picker squares in the text editor toolbar.
# Note the double braces {{ }} — that's because this string uses .format()
# later, and {{ escapes to a literal { in Python f-strings / .format().
COLOR_SWATCH_STYLE = """
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

# Style for action buttons inside panels (Start, Pause, Reset, etc.)
INNER_BUTTON_STYLE = """
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

# Custom thin, semi-transparent scrollbar style (replaces the chunky default).
SCROLLBAR_STYLE = """
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


# =====================================================================
# FloatingPanel – THE BUILDING BLOCK FOR EVERY PANEL
# =====================================================================
#
# WHAT IS A CLASS?
# A class is like a blueprint/template for creating objects. Think of it
# like a cookie cutter — the class defines the shape, and each object
# you create from it is a cookie.
#
# Example:
#   class Dog:
#       def __init__(self, name):    # __init__ runs when you create a new Dog
#           self.name = name         # Each dog has its own name
#       def bark(self):
#           print(f"{self.name} says Woof!")
#
#   my_dog = Dog("Rex")   # Create a Dog object
#   my_dog.bark()          # Prints: "Rex says Woof!"
#
# "self" always refers to "this particular object". If you create two Dogs,
# self.name is different for each one.
#
# WHAT IS INHERITANCE? (the "QWidget" in parentheses)
# "class FloatingPanel(QWidget)" means FloatingPanel INHERITS from QWidget.
# It gets all of QWidget's abilities (showing on screen, receiving mouse
# events, etc.) and can add its own on top. Like saying "a FloatingPanel
# IS a QWidget, but with extra features."
#
# Every feature (Timer, Symbols, Ampel, etc.) lives inside a FloatingPanel.
# A FloatingPanel is a custom window that:
#   - Has a dark title bar with minimize (▬) and close (✕) buttons
#   - Can be dragged around the screen by grabbing its title bar
#   - Can be resized by dragging its edges/corners
#   - Always stays on top of other windows
#   - Has no default Windows title bar (frameless)
#
# HOW IT WORKS (simplified):
#   1. We create a FloatingPanel("Timer")
#   2. We build the panel content (buttons, labels, etc.) as a QWidget
#   3. We call panel.set_content_widget(content) to put it inside the panel
#   4. The panel handles all the dragging/resizing/minimizing automatically

class FloatingPanel(QWidget):
    # --- Signals ---
    # In Qt, a "signal" is an event notification. Other code can "connect" to
    # a signal to run a function whenever the signal fires. For example:
    #   panel.closed.connect(my_function)   # calls my_function when panel closes
    closed = pyqtSignal()       # Emitted when the user clicks the close button
    minimized = pyqtSignal()    # Emitted when the user clicks minimize

    TITLE_BAR_HEIGHT = 32       # Height of the title bar in pixels
    RESIZE_MARGIN = 6           # How close to the edge you need to be to resize

    def __init__(self, title="Panel", parent=None):
        """The constructor — runs once when a new FloatingPanel is created.

        WHAT IS __init__?
        __init__ is a special method that Python calls automatically when you
        create a new object:  panel = FloatingPanel("Timer")
        It sets up the initial state (variables) for this particular panel.

        WHAT IS self?
        'self' refers to THIS specific panel. If you create 3 panels, each
        one has its own self._title, self._is_minimized, etc.

        WHAT IS self._variable (underscore prefix)?
        The _ before a name is a convention meaning "private" — it's used
        internally by this class and shouldn't be accessed from outside.

        WHAT ARE DEFAULT PARAMETERS? (title="Panel")
        If you call FloatingPanel() without arguments, title defaults to "Panel".
        If you call FloatingPanel("Timer"), title will be "Timer".
        """
        # super().__init__() calls QWidget's __init__ — since we inherit from
        # QWidget, we must initialize the parent class first.
        super().__init__(parent)
        self._title = title                 # The text shown in the title bar
        self._is_minimized = False          # Is the panel currently collapsed?
        self._restored_height = 400         # Remember height before minimizing
        self._drag_pos = None               # Mouse position during drag (None = not dragging)
        self._resize_edge = None            # Which edge is being resized (None = not resizing)
        self._resize_start_rect = None      # Panel geometry when resize began
        self._resize_start_pos = None       # Mouse position when resize began
        self._content_widget = None         # The actual content widget inside
        self._setup_window()                # Configure window properties
        self._build_title_bar()             # Build the title bar UI

    def _setup_window(self):
        # WindowFlags control how the OS treats this window:
        #   FramelessWindowHint = no default title bar / border
        #   WindowStaysOnTopHint = always on top of other windows
        #   Tool = don't show in the Windows taskbar
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(180, self.TITLE_BAR_HEIGHT + 20)
        # setMouseTracking(True) means we get mouse-move events even when no
        # button is pressed. Needed to show resize cursors on hover.
        self.setMouseTracking(True)

    def _build_title_bar(self):
        # The panel's overall layout is vertical: title bar on top, content below.
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)  # No padding around edges
        self._main_layout.setSpacing(0)  # No gap between title bar and content

        # --- Title bar widget (the dark strip at the top) ---
        self._title_bar = QWidget(self)
        self._title_bar.setFixedHeight(self.TITLE_BAR_HEIGHT)
        self._title_bar.setStyleSheet(f"""
            background-color: rgba(20, 20, 20, 240);
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
            border-bottom: 1px solid {CARD_BORDER};
        """)

        # Inside the title bar: title text on the left, buttons on the right
        tb_layout = QHBoxLayout(self._title_bar)
        tb_layout.setContentsMargins(10, 0, 4, 0)
        tb_layout.setSpacing(4)

        self._title_label = QLabel(self._title, self._title_bar)
        self._title_label.setStyleSheet("color: white; font-size: 13px; font-weight: bold; background: transparent; border: none;")
        tb_layout.addWidget(self._title_label)
        tb_layout.addStretch()  # Pushes everything after this to the right

        # Minimize button (▬)
        self._btn_minimize = QPushButton("▬", self._title_bar)
        self._btn_minimize.setFixedSize(26, 22)
        self._btn_minimize.setStyleSheet("""
            QPushButton { background: rgba(255,255,255,20); color: white; border: none; border-radius: 3px; font-size: 10px; }
            QPushButton:hover { background: rgba(255,255,255,50); }
        """)
        # .clicked.connect(function) means "when this button is clicked, call function"
        self._btn_minimize.clicked.connect(self.toggle_minimize)
        tb_layout.addWidget(self._btn_minimize)

        # Close button (✕) – red background
        self._btn_close = QPushButton("✕", self._title_bar)
        self._btn_close.setFixedSize(26, 22)
        self._btn_close.setStyleSheet("""
            QPushButton { background: rgba(220,50,50,180); color: white; border: none; border-radius: 3px; font-size: 12px; }
            QPushButton:hover { background: rgba(240,70,70,220); }
        """)
        self._btn_close.clicked.connect(self._on_close)
        tb_layout.addWidget(self._btn_close)

        self._main_layout.addWidget(self._title_bar)

        # --- Content area (the dark body below the title bar) ---
        self._content_area = QWidget(self)
        self._content_area.setStyleSheet(f"background-color: {CARD_BG}; border-bottom-left-radius: 8px; border-bottom-right-radius: 8px;")
        self._content_layout = QVBoxLayout(self._content_area)
        self._content_layout.setContentsMargins(6, 6, 6, 6)
        self._content_layout.setSpacing(0)
        self._main_layout.addWidget(self._content_area)

    def set_content_widget(self, widget):
        """Place a widget inside this panel's content area."""
        self._content_widget = widget
        self._content_layout.addWidget(widget)

    def set_title(self, title):
        """Change the title shown in the title bar."""
        self._title = title
        self._title_label.setText(title)

    def toggle_minimize(self):
        """Collapse the panel to just the title bar, or expand it back."""
        if self._is_minimized:
            # Expand: show content, restore previous height
            self._content_area.show()
            self.setFixedHeight(16777215)  # Remove the fixed height constraint
            self.resize(self.width(), self._restored_height)
            self._is_minimized = False
            self._btn_minimize.setText("▬")
        else:
            # Collapse: save current height, hide content, shrink to title bar
            self._restored_height = self.height()
            self._content_area.hide()
            self.setFixedHeight(self.TITLE_BAR_HEIGHT)
            self._is_minimized = True
            self._btn_minimize.setText("▢")
        self.minimized.emit()  # Notify anyone listening

    def _on_close(self):
        """Hide the panel and emit the closed signal."""
        self.hide()
        self.closed.emit()

    # --- Mouse event handlers for dragging and resizing ---
    # Qt calls these methods automatically when the user interacts with the mouse.
    # "Override" means we replace the default behavior with our own.

    def mousePressEvent(self, event):
        """Called when a mouse button is pressed on this widget."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position().toPoint()  # Mouse position relative to panel
            edge = self._get_resize_edge(pos)
            if edge and not self._is_minimized:
                # Mouse is near an edge → start resizing
                self._resize_edge = edge
                self._resize_start_rect = self.geometry()
                self._resize_start_pos = event.globalPosition().toPoint()
            elif pos.y() <= self.TITLE_BAR_HEIGHT:
                # Mouse is on the title bar → start dragging
                self._drag_pos = event.globalPosition().toPoint() - self.pos()
            else:
                self._drag_pos = None
        super().mousePressEvent(event)  # Let Qt handle anything else

    def mouseMoveEvent(self, event):
        """Called whenever the mouse moves over this widget."""
        pos = event.position().toPoint()
        if self._resize_edge and self._resize_start_pos:
            # Currently resizing → update panel size
            self._do_resize(event.globalPosition().toPoint())
        elif self._drag_pos is not None:
            # Currently dragging → move the panel to follow the mouse
            self.move(event.globalPosition().toPoint() - self._drag_pos)
        else:
            # Not dragging or resizing → just update the cursor shape
            # to show the user what will happen if they click
            edge = self._get_resize_edge(pos)
            if edge and not self._is_minimized:
                # Show a resize cursor (↔, ↕, ⤡, etc.) depending on which edge
                cursors = {
                    "left": Qt.CursorShape.SizeHorCursor, "right": Qt.CursorShape.SizeHorCursor,
                    "top": Qt.CursorShape.SizeVerCursor, "bottom": Qt.CursorShape.SizeVerCursor,
                    "top-left": Qt.CursorShape.SizeFDiagCursor, "bottom-right": Qt.CursorShape.SizeFDiagCursor,
                    "top-right": Qt.CursorShape.SizeBDiagCursor, "bottom-left": Qt.CursorShape.SizeBDiagCursor,
                }
                self.setCursor(cursors.get(edge, Qt.CursorShape.ArrowCursor))
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)  # Normal cursor
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Called when a mouse button is released. Stops any drag/resize."""
        self._drag_pos = None
        self._resize_edge = None
        self._resize_start_rect = None
        self._resize_start_pos = None
        self.setCursor(Qt.CursorShape.ArrowCursor)
        super().mouseReleaseEvent(event)

    def _get_resize_edge(self, pos):
        """Check if the mouse position is near an edge. Returns edge name or None.
        For example: 'left', 'bottom-right', 'top', etc."""
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
        """Calculate new panel geometry based on how far the mouse moved."""
        dx = global_pos.x() - self._resize_start_pos.x()  # Horizontal movement
        dy = global_pos.y() - self._resize_start_pos.y()  # Vertical movement
        r = self._resize_start_rect  # Original rectangle when resize started
        min_w, min_h = self.minimumWidth(), self.minimumHeight()
        new_rect = QRect(r)
        edge = self._resize_edge
        # Adjust the appropriate side(s) of the rectangle, enforcing minimum size
        if "right" in edge: new_rect.setRight(max(r.right() + dx, r.left() + min_w))
        if "bottom" in edge: new_rect.setBottom(max(r.bottom() + dy, r.top() + min_h))
        if "left" in edge: new_rect.setLeft(min(r.left() + dx, r.right() - min_w))
        if "top" in edge: new_rect.setTop(min(r.top() + dy, r.bottom() - min_h))
        self.setGeometry(new_rect)  # Apply the new position + size

    def paintEvent(self, event):
        """Custom drawing: paints the dark rounded-rectangle background.
        Qt calls this automatically whenever the widget needs repainting."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # Smooth edges
        painter.setBrush(QColor(30, 30, 30, 220))      # Fill color
        painter.setPen(QColor(255, 255, 255, 60))       # Border color
        # .adjusted(1,1,-1,-1) shrinks the rect by 1px so the border fits inside
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 8, 8)
        painter.end()


# =====================================================================
# OverlayToolbar – THE BAR AT THE TOP OF THE SCREEN
# =====================================================================
# This is the thin dark bar across the top that has buttons to toggle
# each panel on/off, a class selector, minimize-all, and quit.
# It's also frameless and always-on-top, just like FloatingPanel.

class OverlayToolbar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._panel_buttons = {}  # Dict mapping panel_id → button widget
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
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(8, 4, 8, 4)
        self._layout.setSpacing(6)
        handle = QLabel("⠿", self)
        handle.setStyleSheet("color: rgba(255,255,255,60); font-size: 18px; background: transparent; border: none;")
        self._layout.addWidget(handle)
        self._layout.addStretch()

    def add_panel_button(self, panel_id, label, callback, enabled=True):
        """Create a toggle button in the toolbar for showing/hiding a panel.
        'callback' is the function called when the button is clicked.
        'panel_id' is a unique string like 'timer' or 'symbols'."""
        btn = QPushButton(label, self)
        btn.setCheckable(True)   # Makes it a toggle: stays pressed/unpressed
        btn.setChecked(True if enabled else False)
        btn.setEnabled(enabled)
        btn.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        if enabled and callback:
            btn.clicked.connect(callback)
        if not enabled:
            btn.setToolTip("Kommt bald!")  # "Coming soon!" tooltip
        # Insert before the last stretch so it stays left-aligned
        self._layout.insertWidget(self._layout.count() - 1, btn)
        self._panel_buttons[panel_id] = btn
        return btn

    def add_separator(self):
        sep = QFrame(self)
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,40); background: transparent; border: none;")
        sep.setFixedWidth(2)
        self._layout.insertWidget(self._layout.count() - 1, sep)

    def add_quit_button(self, callback):
        self._layout.addStretch()
        btn = QPushButton("✕ Beenden", self)
        btn.setStyleSheet("""
            QPushButton { background-color: rgba(180,40,40,200); color: white; border: 1px solid rgba(255,80,80,120); border-radius: 4px; padding: 5px 14px; font-size: 13px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(220,60,60,230); }
            QPushButton:pressed { background-color: rgba(150,30,30,255); }
        """)
        btn.clicked.connect(callback)
        self._layout.addWidget(btn)

    def add_minimize_button(self, callback):
        btn = QPushButton("⬇", self)
        btn.setStyleSheet("""
            QPushButton { background-color: rgba(80,80,80,200); color: white; border: 1px solid rgba(255,255,255,60); border-radius: 4px; padding: 5px 10px; font-size: 14px; font-weight: bold; }
            QPushButton:hover { background-color: rgba(100,100,100,230); }
        """)
        btn.setToolTip("Alles minimieren")
        btn.clicked.connect(callback)
        self._layout.addWidget(btn)
        return btn

    def add_class_selector_button(self, callback):
        btn = QPushButton("📚 Klasse", self)
        btn.setStyleSheet(TOOLBAR_BUTTON_STYLE)
        btn.clicked.connect(callback)
        self._layout.insertWidget(self._layout.count() - 1, btn)
        self._panel_buttons["class_selector"] = btn
        return btn

    def set_button_checked(self, panel_id, checked):
        btn = self._panel_buttons.get(panel_id)
        if btn:
            btn.setChecked(checked)

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
        painter.setBrush(QColor(15, 15, 15, 235))
        painter.setPen(QColor(255, 255, 255, 40))
        painter.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 6, 6)
        painter.end()


# ---------------------------------------------------------------------------
# RestoreButton – tiny button shown when everything is minimized
# ---------------------------------------------------------------------------

class RestoreButton(QWidget):
    clicked = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setFixedSize(48, 48)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        btn = QPushButton("▲", self)
        btn.setFixedSize(48, 48)
        btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(0, 120, 215, 220);
                color: white; border: 2px solid rgba(255,255,255,100);
                border-radius: 24px; font-size: 20px; font-weight: bold;
            }
            QPushButton:hover { background-color: rgba(0, 140, 235, 240); }
        """)
        btn.setToolTip("Overlay wiederherstellen")
        btn.clicked.connect(self.clicked.emit)
        layout.addWidget(btn)

    def paintEvent(self, event):
        pass  # transparent background


# ---------------------------------------------------------------------------
# FormattingToolbar – rich text formatting buttons
# ---------------------------------------------------------------------------
# This toolbar sits above the text editor. It has buttons for:
#   Bold (B), Italic (I), Underline (U), font size +/-, text color, highlight.
# It modifies the selected text inside the QTextEdit using QTextCharFormat.
#
# KEY CONCEPT: QTextCharFormat
#   When you select text in a QTextEdit, you can apply formatting to just that
#   selection. QTextCharFormat describes the formatting (bold? italic? color?).
#   You create a format, set properties on it, then apply it via:
#     cursor = text_edit.textCursor()
#     cursor.mergeCharFormat(my_format)

class FormattingToolbar(QWidget):
    # Predefined color palettes for quick color selection
    QUICK_COLORS = ["#FF4444", "#FF8800", "#FFDD00", "#44DD44", "#4488FF", "#AA44FF", "#FFFFFF", "#000000"]
    QUICK_HIGHLIGHTS = ["#FFFF00", "#00FF00", "#00DDFF", "#FF8800", "#FF4444", "#DD88FF", "#FFFFFF", "transparent"]

    def __init__(self, text_edit, parent=None):
        super().__init__(parent)
        self.text_edit = text_edit  # Reference to the text editor we're formatting
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
        scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")

        inner = QWidget()
        inner.setStyleSheet("background: transparent; border: none;")
        layout = QHBoxLayout(inner)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(3)

        self.btn_bold = QPushButton("B", inner)
        self.btn_bold.setCheckable(True)
        self.btn_bold.setStyleSheet(FORMAT_BUTTON_STYLE)
        self.btn_bold.setToolTip("Fett (Strg+B)")
        self.btn_bold.clicked.connect(self._toggle_bold)
        layout.addWidget(self.btn_bold)

        self.btn_italic = QPushButton("I", inner)
        self.btn_italic.setCheckable(True)
        self.btn_italic.setStyleSheet(FORMAT_BUTTON_STYLE)
        self.btn_italic.setToolTip("Kursiv (Strg+I)")
        self.btn_italic.clicked.connect(self._toggle_italic)
        layout.addWidget(self.btn_italic)

        self.btn_underline = QPushButton("U", inner)
        self.btn_underline.setCheckable(True)
        self.btn_underline.setStyleSheet(FORMAT_BUTTON_STYLE)
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
        for size in [10, 12, 14, 16, 18, 20, 24, 28, 32, 40]:
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
            btn.setStyleSheet(COLOR_SWATCH_STYLE.format(color=color))
            btn.clicked.connect(lambda checked, c=color: self._set_text_color(c))
            layout.addWidget(btn)
        btn_more = QPushButton("…", inner)
        btn_more.setStyleSheet(FORMAT_BUTTON_STYLE)
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
                btn.setStyleSheet(COLOR_SWATCH_STYLE.format(color=color))
            btn.clicked.connect(lambda checked, c=color: self._set_highlight_color(c))
            layout.addWidget(btn)
        btn_more_hl = QPushButton("…", inner)
        btn_more_hl.setStyleSheet(FORMAT_BUTTON_STYLE)
        btn_more_hl.clicked.connect(self._pick_highlight_color)
        layout.addWidget(btn_more_hl)

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


# =====================================================================
# PANEL CREATOR FUNCTIONS
# =====================================================================
# Each function below creates one feature panel. The pattern is always:
#   1. Create a FloatingPanel with a title
#   2. Create a content QWidget and add buttons/labels/etc. to it
#   3. Call panel.set_content_widget(content) to put it in the panel
#   4. Wire up signal/slot connections (button clicks → functions)
#   5. Set up a resize handler so everything scales with window size
#   6. Return the panel
# =====================================================================


# ---------------------------------------------------------------------------
# TEXT EDITOR PANEL
# ---------------------------------------------------------------------------
# A rich text editor with a formatting toolbar (bold, italic, underline,
# font size, text color). Supports Ctrl+B / Ctrl+I / Ctrl+U shortcuts.

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
        {SCROLLBAR_STYLE}
    """)
    text_edit.setPlaceholderText("Hier Text eingeben…")
    text_edit.setAcceptRichText(True)
    text_edit.setFont(QFont("Segoe UI", 14))

    toolbar = FormattingToolbar(text_edit, content)
    cl.addWidget(toolbar)
    cl.addWidget(text_edit)
    panel.set_content_widget(content)
    panel.text_edit = text_edit
    panel.formatting_toolbar = toolbar

    # --- Keyboard shortcuts ---
    # QShortcut binds a key combination (like Ctrl+B) to a function.
    # WidgetShortcut means the shortcut only works when the text editor has focus.
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


# ---------------------------------------------------------------------------
# STUDENT LIST PANEL (Schülerliste)
# ---------------------------------------------------------------------------
# Shows the currently loaded class with all student names in a scrollable list.

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
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")
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


def load_students_into_panel(panel, class_name, students):
    panel.header_label.setText(f"📋 Klasse {class_name}")
    panel.set_title(f"📋 Klasse {class_name}")
    layout = panel.student_layout
    while layout.count() > 1:
        item = layout.takeAt(0)
        w = item.widget()
        if w: w.deleteLater()
    for i, s in enumerate(students, 1):
        lbl = QLabel(f"  {i}. {s.get('first_name','')} {s.get('last_name','')}", panel.student_container)
        lbl.setStyleSheet("color: white; font-size: 14px; background: transparent; border: none; padding: 3px 6px;")
        layout.insertWidget(layout.count() - 1, lbl)


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


# ---------------------------------------------------------------------------
# CLASS EDITOR PANEL (Klasse erstellen / bearbeiten)
# ---------------------------------------------------------------------------
# Lets the teacher create a new class or edit an existing one.
# Has input fields for class name and student names, with add/remove buttons.

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
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")
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
    btn_add.setStyleSheet(INNER_BUTTON_STYLE)
    btn_add.clicked.connect(lambda: add_row(focus_first=True))
    cl.addWidget(btn_add)

    # Save button
    btn_save = QPushButton("💾 Klasse speichern", content)
    btn_save.setStyleSheet(INNER_BUTTON_STYLE)
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


# =====================================================================
# TIMER / STOPWATCH PANEL
# =====================================================================
# Two modes:
#   Timer mode:     Count DOWN from a set time (e.g. 5:00 → 0:00)
#   Stopwatch mode: Count UP from 0:00
#
# Features:
#   - Visual circular countdown clock (pie chart)
#   - +/- buttons above/below each digit to adjust time on the fly
#   - Start / Pause / Reset buttons
#   - Everything scales with window size
# =====================================================================


class CountdownClockWidget(QWidget):
    """A circular pie-chart countdown clock drawn with QPainter.

    HOW CUSTOM DRAWING WORKS IN QT:
    When you want to draw something that doesn't exist as a standard widget
    (like a pie chart), you create a custom widget and override paintEvent().
    Qt calls paintEvent() every time the widget needs redrawing. Inside it,
    you use QPainter to draw shapes, text, images, etc.

    This widget draws:
    1. A dark circle (background)
    2. A colored pie slice showing remaining time (green → yellow → red)
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self._progress = 1.0  # 1.0 = full circle (all time left), 0.0 = empty
        self._color = QColor(0, 180, 80)  # Start green
        self.setMinimumSize(60, 60)

    def set_progress(self, fraction):
        """Update the pie chart. fraction: 0.0 (empty) to 1.0 (full)."""
        self._progress = max(0.0, min(1.0, fraction))
        # Automatically change color based on how much time is left
        if self._progress > 0.5:
            self._color = QColor(0, 180, 80)    # Green: more than half left
        elif self._progress > 0.25:
            self._color = QColor(255, 200, 0)   # Yellow: quarter to half left
        else:
            self._color = QColor(220, 50, 50)   # Red: less than a quarter left
        self.update()  # Tell Qt to repaint this widget

    def paintEvent(self, event):
        """Draw the countdown clock. Called automatically by Qt."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)  # Smooth edges

        # Make the clock as large as possible while fitting in the widget
        side = min(self.width(), self.height()) - 4
        x = (self.width() - side) // 2   # Center horizontally
        y = (self.height() - side) // 2  # Center vertically
        rect = QRect(x, y, side, side)

        # Draw background circle (dark with faint white border)
        painter.setPen(QPen(QColor(255, 255, 255, 40), 2))
        painter.setBrush(QBrush(QColor(40, 40, 40, 180)))
        painter.drawEllipse(rect)

        # Draw the colored pie slice showing remaining time
        if self._progress > 0.001:
            painter.setPen(Qt.PenStyle.NoPen)  # No outline on the pie
            painter.setBrush(QBrush(self._color))
            # Qt measures angles in 1/16th of a degree.
            # 90 * 16 = start at 12 o'clock (top). span = how much to fill.
            span = int(self._progress * 360 * 16)
            painter.drawPie(rect.adjusted(3, 3, -3, -3), 90 * 16, span)
        painter.end()


def create_timer_panel():
    """Create the Timer / Stopwatch panel with all controls."""
    panel = FloatingPanel("⏱ Timer / Stoppuhr")
    panel.setMinimumSize(260, 250)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # --- Mode toggle buttons (Timer vs Stoppuhr) ---
    # QHBoxLayout arranges widgets left-to-right in a row
    mode_row = QHBoxLayout()
    btn_timer = QPushButton("⏱ Timer", content)
    btn_timer.setCheckable(True)    # Makes it a toggle button (stays pressed)
    btn_timer.setChecked(True)      # Start with Timer mode selected
    btn_timer.setStyleSheet(FORMAT_BUTTON_STYLE)
    btn_stopwatch = QPushButton("⏱ Stoppuhr", content)
    btn_stopwatch.setCheckable(True)
    btn_stopwatch.setStyleSheet(FORMAT_BUTTON_STYLE)
    mode_row.addWidget(btn_timer)       # Add button to the row
    mode_row.addWidget(btn_stopwatch)
    mode_row.addStretch()   # Push buttons to the left, empty space on the right
    cl.addLayout(mode_row)  # Add the row to the main vertical layout

    # --- Circular countdown clock (the pie chart) ---
    clock_widget = CountdownClockWidget(content)
    # SizePolicy.Expanding means "grow to fill available space"
    clock_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    cl.addWidget(clock_widget, 1)  # The "1" gives it stretch priority

    # --- +/- digit adjustment buttons + display ---
    # Layout (top to bottom): [+] buttons, time display (05:00), [-] buttons
    # Each +/- button adjusts one digit of the time (min10, min1, sec10, sec1)

    # This function GENERATES a stylesheet string. It's a function (not a constant)
    # because the font size and button size change when the window is resized.
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

    # --- Row of [+] buttons above the time display ---
    plus_row = QHBoxLayout()
    plus_row.setSpacing(2)      # 2px gap between buttons
    plus_row.addStretch()       # Center the buttons
    plus_btns = []              # We'll store all 4 [+] buttons in this list
    pm_spacers = []             # Spacer labels between minutes and seconds
    # range(4) gives us [0, 1, 2, 3] — one for each digit position
    for _ in range(4):  # _ means we don't need the loop variable's value
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

    # --- Time display label (shows "05:00") ---
    # We use a dictionary to track the current color. Why a dict and not just
    # a variable? Because Python closures (inner functions) can read outer
    # variables but can't reassign them. Dicts are mutable, so we can modify
    # the value inside without reassigning the variable itself.
    timer_font_state = {"color": "white"}

    def get_timer_font_size():
        """Calculate font size based on panel width. Bigger panel = bigger text.
        max(20, ...) ensures minimum size of 20px.
        min(120, ...) caps it at 120px so it doesn't get absurdly large."""
        return max(20, min(120, content.width() // 6))

    display = QLabel("05:00", content)
    display.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def make_display_style(color=None):
        if color:
            timer_font_state["color"] = color
        c = timer_font_state["color"]
        sz = get_timer_font_size()
        return f"color: {c}; font-size: {sz}px; font-weight: bold; font-family: 'Consolas', monospace; background: transparent; border: none;"

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
    cl.addWidget(input_widget)

    # Buttons
    btn_row = QHBoxLayout()
    btn_start = QPushButton("▶ Start", content)
    btn_start.setStyleSheet(INNER_BUTTON_STYLE)
    btn_pause = QPushButton("⏸ Pause", content)
    btn_pause.setStyleSheet(INNER_BUTTON_STYLE)
    btn_reset = QPushButton("↺ Reset", content)
    btn_reset.setStyleSheet(INNER_BUTTON_STYLE)
    btn_row.addWidget(btn_start)
    btn_row.addWidget(btn_pause)
    btn_row.addWidget(btn_reset)
    cl.addLayout(btn_row)

    panel.set_content_widget(content)

    # --- Timer state ---
    # QTimer is Qt's built-in timer. It fires a signal ("timeout") at regular
    # intervals. We set it to fire every 100 milliseconds (0.1 seconds).
    # Each time it fires, our "tick" function updates the countdown.
    timer = QTimer()
    timer.setInterval(100)  # Fire every 100ms

    # We store the timer's state in a dictionary. This is a common pattern:
    # instead of many separate variables, group related data together.
    # "ms" = current time in milliseconds, "target_ms" = total time set
    # 300000 ms = 5 minutes (5 × 60 × 1000)
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
                display.setStyleSheet(make_display_style("#FF4444"))
        else:
            state["ms"] += 100
        update_display()

    timer.timeout.connect(tick)

    def start():
        if state["mode"] == "timer" and not state["running"]:
            if state["ms"] == 0:
                state["ms"] = (spin_min.value() * 60 + spin_sec.value()) * 1000
                state["target_ms"] = state["ms"]
        display.setStyleSheet(make_display_style("white"))
        state["running"] = True
        timer.start()

    def pause():
        timer.stop()
        state["running"] = False

    def reset():
        timer.stop()
        state["running"] = False
        state["ms"] = 0 if state["mode"] == "stopwatch" else (spin_min.value() * 60 + spin_sec.value()) * 1000
        if state["mode"] == "timer":
            state["target_ms"] = state["ms"]
        display.setStyleSheet(make_display_style("white"))
        update_display()

    # --- +/- button handlers: adjust time on the fly ---
    # Each digit position adds a different amount of time:
    # Position 0 (tens of minutes): +/- 10 minutes = 600,000 ms
    # Position 1 (ones of minutes): +/- 1 minute  = 60,000 ms
    # Position 2 (tens of seconds): +/- 10 seconds = 10,000 ms
    # Position 3 (ones of seconds): +/- 1 second   = 1,000 ms
    increments = [10 * 60 * 1000, 1 * 60 * 1000, 10 * 1000, 1 * 1000]

    def adjust_time(delta_ms):
        """Add or subtract time. delta_ms can be positive (+) or negative (-)."""
        state["ms"] = max(0, state["ms"] + delta_ms)  # Don't go below 0
        state["target_ms"] = max(state["target_ms"], state["ms"])
        update_display()

    # Connect each +/- button to adjust_time with the right increment.
    #
    # WHAT IS lambda?
    # A lambda is a tiny one-line function without a name.
    # "lambda checked, d=increments[i]: adjust_time(d)" means:
    #   "create a function that takes 'checked' (ignored) and calls adjust_time(d)"
    #
    # WHY "d=increments[i]"?
    # This is a Python trick. Without it, all 4 buttons would use the LAST value
    # of i (which is 3). By writing d=increments[i], we "capture" the current
    # value at the time the lambda is created. This is a common gotcha in Python!
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

    btn_start.clicked.connect(start)
    btn_pause.clicked.connect(pause)
    btn_reset.clicked.connect(reset)
    btn_timer.clicked.connect(set_timer_mode)
    btn_stopwatch.clicked.connect(set_stopwatch_mode)

    # --- Resize handler — scale ALL elements to window size ---
    # HOW DYNAMIC SCALING WORKS:
    # Every time the panel is resized, Qt calls content.resizeEvent().
    # We override it (replace the function) with our own that calculates
    # new font sizes, button sizes, etc. based on the current width/height.
    # We use min(width, height) as a "scale" factor so everything stays
    # proportional whether you resize horizontally or vertically.
    timer_action_btns = [btn_start, btn_pause, btn_reset]
    timer_mode_btns = [btn_timer, btn_stopwatch]
    orig_resize = content.resizeEvent  # Save the original handler
    def on_timer_resize(event):
        if orig_resize:
            orig_resize(event)  # Call the original handler first
        w = content.width()
        h = content.height()
        scale = min(w, h)  # Use the smaller dimension for proportional scaling

        # Display digits
        display.setStyleSheet(make_display_style())

        # +/- buttons
        pm_fsz = max(10, scale // 20)
        pm_w = max(20, scale // 14)
        pm_h = max(16, scale // 18)
        pm_style = make_pm_btn_style(pm_fsz, pm_w, pm_h)
        for b in plus_btns + minus_btns:
            b.setStyleSheet(pm_style)
        spacer_w = max(8, scale // 30)
        for s in pm_spacers:
            s.setFixedWidth(spacer_w)

        # Mode toggle buttons
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

        # Start / Pause / Reset buttons
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

        # Spin boxes and labels
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

    content.resizeEvent = on_timer_resize

    update_display()
    return panel


# =====================================================================
# RANDOM NAME PICKER + GROUP MAKER PANEL (Zufall / Gruppen)
# =====================================================================
# Two features in one panel:
#   1. Random Name Picker: picks a random student from the loaded class
#   2. Group Maker: divides all students into N random groups

def create_random_panel(get_students_fn):
    """get_students_fn: a function that returns (class_name, [students]) or None.
    This is how the panel gets access to the currently loaded class."""
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
    btn_pick.setStyleSheet(INNER_BUTTON_STYLE)
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
    btn_shuffle.setStyleSheet(INNER_BUTTON_STYLE)
    group_input_row.addWidget(lbl_groups)
    group_input_row.addWidget(spin_groups)
    group_input_row.addWidget(btn_shuffle)
    group_input_row.addStretch()
    cl.addLayout(group_input_row)

    # Group results scroll area
    group_scroll = QScrollArea(content)
    group_scroll.setWidgetResizable(True)
    group_scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")
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


class DraggableStudentLabel(QLabel):
    """A label that can be dragged in sort mode."""
    def __init__(self, student_key, color, state, refresh_fn, parent=None):
        super().__init__(f"  {student_key}", parent)
        self._student_key = student_key
        self._color = color
        self._state = state
        self._refresh_fn = refresh_fn
        self.setStyleSheet(
            "QLabel { color: white; background: rgba(255,255,255,10); "
            "border: 1px solid rgba(255,255,255,20); border-radius: 4px; padding: 4px 8px;}"
        )
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setWordWrap(False)
        self.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(0)


    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self._start_pos = event.position().toPoint()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.MouseButton.LeftButton:
            if hasattr(self, '_start_pos'):
                diff = event.position().toPoint() - self._start_pos
                if diff.manhattanLength() > 10:
                    drag = QDrag(self)
                    mime = QMimeData()
                    mime.setText(self._student_key)
                    drag.setMimeData(mime)
                    # Make the drag pixmap semi-transparent
                    pixmap = self.grab()
                    p = QPainter(pixmap)
                    p.setCompositionMode(QPainter.CompositionMode.CompositionMode_DestinationIn)
                    p.fillRect(pixmap.rect(), QColor(0, 0, 0, 150))
                    p.end()
                    drag.setPixmap(pixmap)
                    drag.setHotSpot(event.position().toPoint())
                    drag.exec(Qt.DropAction.MoveAction)
                    self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)


class DropZoneWidget(QWidget):
    """A drop zone for a traffic light color section with reflowing student labels."""
    def __init__(self, color_name, state, refresh_fn, parent=None):
        super().__init__(parent)
        self._color_name = color_name
        self._state = state
        self._refresh_fn = refresh_fn
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

    def set_scroll_viewport(self, fn):
        self._scroll_viewport_fn = fn

    def add_student(self, student_key):
        lbl = DraggableStudentLabel(student_key, self._color_name, self._state, self._refresh_fn, self)
        self._student_lbls.append(lbl)

    def apply_font_size(self, fsz):
        font = self._header_lbl.font()
        font.setPointSize(fsz + 2)
        self._header_lbl.setFont(font)
        for lbl in self._student_lbls:
            font = lbl.font()
            font.setPointSize(fsz)
            lbl.setFont(font)
            lbl.updateGeometry()
        self.updateGeometry()

    def reflow_students(self):
        clear_layout(self._students_layout)
        if not self._student_lbls: return

        # Get available width from the scroll area's viewport
        viewport_width = self.width()
        if self._scroll_viewport_fn:
            viewport_width = self._scroll_viewport_fn().width()

        # Calculate column width from font metrics of the widest name
        if self._student_lbls:
            fm = self._student_lbls[0].fontMetrics()
            max_text_w = max(fm.horizontalAdvance(lbl.text()) for lbl in self._student_lbls)
            col_w = max(60, max_text_w + 30)  # +30 for padding/border
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
            self.setStyleSheet(
                f"background: rgba({','.join(str(c) for c in QColor(LIGHT_COLORS[self._color_name]).getRgb()[:3])}, 40); "
                f"border: 2px dashed {LIGHT_COLORS[self._color_name]}; border-radius: 6px;"
            )

    def dragLeaveEvent(self, event):
        self._highlight = False
        self.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,15); border-radius: 6px;")

    def dropEvent(self, event):
        student_key = event.mimeData().text()
        if student_key:
            self._state["lights"][student_key] = self._color_name
            self._highlight = False
            self.setStyleSheet("background: transparent; border: 1px solid rgba(255,255,255,15); border-radius: 6px;")
            event.acceptProposedAction()
            self._refresh_fn()


# =====================================================================
# TRAFFIC LIGHT PANEL (Ampel)
# =====================================================================
# Shows each student with a colored dot (green/yellow/red).
# Two modes:
#   Klick-Modus: Click a student's dot to cycle through colors
#   Sortier-Modus: Drag and drop students into color zones
# Also has a "Regeln" (rules) section where you can write rules for each color.
# Names auto-scale using binary search with QFontMetrics so all names are
# always visible without scrolling.

def create_traffic_light_panel(get_students_fn):
    panel = FloatingPanel("🚦 Ampelsystem")
    panel.setMinimumSize(260, 350)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(10, 10, 10, 10)
    cl.setSpacing(6)

    # Mode toggle
    mode_row = QHBoxLayout()
    btn_click_mode = QPushButton("Klick-Modus", content)
    btn_click_mode.setCheckable(True)
    btn_click_mode.setChecked(True)
    btn_click_mode.setStyleSheet(FORMAT_BUTTON_STYLE)
    btn_sort_mode = QPushButton("Sortier-Modus", content)
    btn_sort_mode.setCheckable(True)
    btn_sort_mode.setStyleSheet(FORMAT_BUTTON_STYLE)
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
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")
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
    btn_reset.setStyleSheet(INNER_BUTTON_STYLE)
    cl.addWidget(btn_reset)

    # Rules text areas (one per color)
    rules_header = QPushButton("📋 Regeln ▾", content)
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
        text_edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        def resize_text_edit():
            # Use min/max height to allow layout to adjust
            doc_height = text_edit.document().documentLayout().documentSize().height()
            margins = text_edit.contentsMargins()
            frame = text_edit.frameWidth() * 2
            h = int(doc_height + margins.top() + margins.bottom() + frame)
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

    cl.addWidget(rules_container)

    def toggle_rules():
        visible = rules_header.isChecked()
        rules_container.setVisible(visible)
        rules_header.setText("📋 Regeln ▾" if visible else "📋 Regeln ▸")

    rules_header.clicked.connect(toggle_rules)

    panel.set_content_widget(content)

    state = {
        "students": [], "lights": {}, "mode": "click",
        "name_widgets": [], "sort_zones": {},
        "base_rule_size": 12,
    }

    def student_key(s):
        return f"{s.get('first_name','')} {s.get('last_name','')}"

    def clear_name_widgets():
        clear_layout(scroll_layout) # This removes from layout first.

        for w in state["name_widgets"]:
            w[-1].deleteLater() # w[-1] is now parentless.
        state["name_widgets"] = []
        
        for zone in state["sort_zones"].values():
            zone.deleteLater() # zone is now parentless
        state["sort_zones"] = {}


    def calc_name_font_size():
        """Find the largest font size (8-28) where ALL names fit on screen.

        HOW THE BINARY SEARCH WORKS:
        We want the biggest font that still lets all names fit without scrolling.
        Instead of trying every size from 8 to 28, binary search is faster:
          1. Try the middle size (18). Does it fit? → try bigger. Doesn't fit? → try smaller.
          2. Repeat, narrowing the range each time, until we find the exact max.

        For each candidate font size, we SIMULATE the layout using QFontMetrics:
          - QFontMetrics tells us how wide/tall text would be at that font size
          - We calculate: widest name → column width → how many columns fit →
            how many rows needed → total height
          - If total height <= viewport height, it fits!

        This approach avoids actually rendering anything — it's pure math."""
        vp_w = max(1, scroll.viewport().width())   # Available width
        vp_h = max(1, scroll.viewport().height())   # Available height
        n = len(state["students"])
        if n == 0:
            return 14  # Default size when no students loaded
        names = [student_key(s) for s in state["students"]]

        def fits_click(fsz):
            """Check if all names fit in click-mode layout at font size fsz."""
            font = QFont()
            font.setPointSize(fsz)
            fm = QFontMetrics(font)  # Measures text at this font size
            row_h = fm.height() + 4
            dot_size = max(18, int(fm.height() * 1.2))  # The colored dot
            max_name_w = max(fm.horizontalAdvance(name) for name in names)
            col_w = max(80, max_name_w + dot_size + 30)  # Width of one column
            num_cols = max(1, (vp_w - 8) // col_w)       # How many columns fit
            num_rows = math.ceil(n / num_cols)            # Rows needed
            total_h = 8 + num_rows * row_h + max(0, num_rows - 1) * 6
            return total_h <= vp_h  # True if it fits!

        def fits_sort(fsz):
            font = QFont()
            font.setPointSize(fsz)
            fm = QFontMetrics(font)
            hdr_font = QFont()
            hdr_font.setPointSize(fsz + 2)
            hdr_fm = QFontMetrics(hdr_font)
            row_h = fm.height() + 12
            header_h = hdr_fm.height() + 8
            total_h = 8
            for color in LIGHT_ORDER:
                total_h += header_h + 4
                zone_names = [student_key(s) for s in state["students"]
                              if state["lights"].get(student_key(s), "green") == color]
                if zone_names:
                    max_w = max(fm.horizontalAdvance(f"  {nm}") for nm in zone_names)
                    col_w = max(60, max_w + 30)
                    nc = max(1, (vp_w - 28) // col_w)
                    nr = math.ceil(len(zone_names) / nc)
                    total_h += nr * row_h + max(0, nr - 1) * 4
                total_h += 8
            return total_h <= vp_h

        fits_fn = fits_sort if state["mode"] == "sort" else fits_click
        lo, hi, result = 8, 28, 8
        while lo <= hi:
            mid = (lo + hi) // 2
            if fits_fn(mid):
                result = mid
                lo = mid + 1
            else:
                hi = mid - 1
        return result

    def apply_font_to_students(fsz):
        if state["mode"] == "click":
             for _, name_lbl, _, container in state["name_widgets"]:
                font = name_lbl.font()
                font.setPointSize(fsz)
                name_lbl.setFont(font)
                #container.setMinimumWidth(name_lbl.sizeHint().width() + 50) 
        elif state["mode"] == "sort":
            for zone in state["sort_zones"].values():
                zone.apply_font_size(fsz)

    def apply_ampel_scale():
        if not state["name_widgets"] or state["mode"] != 'click': return
        for light_btn, name_lbl, key, _ in state["name_widgets"]:
            color = state["lights"].get(key, "green")
            # Make dot size relative to name height, but a bit larger
            dot_size = int(name_lbl.fontMetrics().height() * 1.2)
            if dot_size < 18: dot_size = 18
            light_btn.setFixedSize(dot_size, dot_size)
            # Make icon size fill the button
            dot_font_size = int(dot_size * 0.8)
            light_btn.setStyleSheet(
                f"QPushButton {{ color: {LIGHT_COLORS[color]}; font-size: {dot_font_size}px; text-align: center; background: transparent; border: none; }}"
                f"QPushButton:hover {{ background: rgba(255,255,255,20); border-radius: {dot_size // 2}px; }}"
            )

    def reflow_ampel_layout():
        clear_layout(scroll_layout)
        
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
                    scroll_layout.addWidget(zone, i, 0)
                    zone.reflow_students() # Tell the zone to reflow its internal grid
            scroll_layout.setRowStretch(len(LIGHT_ORDER), 1)
            scroll_layout.setColumnStretch(1, 1)


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
            name_lbl = QLabel(key, container)
            name_lbl.setWordWrap(False)
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
            name_lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            font = name_lbl.font()
            font.setPointSize(fsz)
            name_lbl.setFont(font)

            def cycle(checked=False, k=key):
                cur = state["lights"].get(k, "green")
                nxt = LIGHT_ORDER[(LIGHT_ORDER.index(cur) + 1) % 3]
                state["lights"][k] = nxt
                refresh()

            light_btn.clicked.connect(cycle)
            rl.addWidget(light_btn)
            rl.addWidget(name_lbl)
            rl.addStretch() # Stretch inside the hbox

            state["name_widgets"].append((light_btn, name_lbl, key, container))
        
    def render_sort_mode():
        clear_name_widgets()
        
        for color_name in LIGHT_ORDER:
            drop_zone = DropZoneWidget(color_name, state, refresh, scroll_content)
            drop_zone.set_scroll_viewport(scroll.viewport) # Pass viewport for width calculations
            
            students_in_color = [s for s in state["students"] if state["lights"].get(student_key(s), "green") == color_name]
            for s in students_in_color:
                drop_zone.add_student(student_key(s))

            state["sort_zones"][color_name] = drop_zone

    def refresh():
        content.blockSignals(True)
        if state["mode"] == "click":
            render_click_mode()
        else:
            render_sort_mode()
        # Trigger a full resize/reflow after rendering widgets
        QTimer.singleShot(0, lambda: on_ampel_resize(None))
        content.blockSignals(False)

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
        refresh()

    btn_click_mode.clicked.connect(set_click_mode)
    btn_sort_mode.clicked.connect(set_sort_mode)
    btn_reset.clicked.connect(reset_all)

    def load_students(students):
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

    # --- Main Resize Logic ---
    # This is the most important part of the Ampel panel: whenever the panel
    # is resized, we recalculate font sizes so all names always fit.
    # We override scroll.resizeEvent (not content.resizeEvent) because the
    # scroll area's viewport dimensions are more up-to-date at resize time.
    orig_scroll_resize = scroll.resizeEvent
    def on_ampel_resize(event):
        if orig_scroll_resize and event is not None:
            orig_scroll_resize(event)

        # Use the binary-search function to find the best font size
        fsz = calc_name_font_size()
        apply_font_to_students(fsz)

        # --- Rules Area Scaling ---
        rule_offset = state["base_rule_size"] - 12  # 12 is default
        rule_font_size = max(8, min(20, content.width() // 50 + rule_offset))
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

        # --- Final Reflow & Repaint ---
        reflow_ampel_layout()
        apply_ampel_scale()
    scroll.resizeEvent = on_ampel_resize

    # --- Font size controls ---
    font_control_style = """
        QPushButton {
            background-color: rgba(70, 70, 70, 220); color: white;
            border: 1px solid rgba(255, 255, 255, 80); border-radius: 5px;
            font-size: 14px; font-weight: bold; min-width: 28px; max-width: 28px;
        }
        QPushButton:hover { background-color: rgba(100, 100, 100, 230); }
        QPushButton:pressed { background-color: rgba(50, 50, 50, 255); }
        QLabel { color: white; font-size: 13px; background: transparent; border: none; }
    """
    rule_font_row = QHBoxLayout()
    rule_font_lbl = QLabel("Schrift (Regeln):", content)
    btn_rule_font_down = QPushButton("⬇", content)
    btn_rule_font_up = QPushButton("⬆", content)
    btn_rule_font_down.setStyleSheet(font_control_style)
    btn_rule_font_up.setStyleSheet(font_control_style)
    rule_font_row.addWidget(rule_font_lbl)
    rule_font_row.addStretch()
    rule_font_row.addWidget(btn_rule_font_down)
    rule_font_row.addWidget(btn_rule_font_up)

    # Insert font controls above the main scroll area
    cl.insertLayout(1, rule_font_row)

    def change_rule_font(delta):
        state["base_rule_size"] = max(8, state["base_rule_size"] + delta)
        on_ampel_resize(None)

    btn_rule_font_up.clicked.connect(lambda: change_rule_font(1))
    btn_rule_font_down.clicked.connect(lambda: change_rule_font(-1))

    return panel


# =====================================================================
# WORK SYMBOLS PANEL (Arbeitssymbole)
# =====================================================================
# Shows big emoji/image symbols to tell students what kind of work they
# should be doing (reading, writing, group work, etc.).
# Features:
#   - Toggle symbols on/off with a grid of buttons
#   - Active symbols appear large in a display area at the top
#   - Custom symbols via file picker; right-click to replace/delete
#   - Everything auto-scales with window size
#   - Selection grid can be hidden with a toggle button

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

    # WHAT IS A SET?
    # A set is like a list, but with no duplicates and no order.
    # set() creates an empty set. We use it to track which symbols are "active"
    # (toggled on). Adding/removing from a set is very fast.
    active_set = set()
    buttons = {}  # Dictionary mapping symbol key → button widget

    # Track all symbols: built-in emojis + custom images.
    # Each entry is a dictionary with: key, emoji, image path, and label text.
    #
    # WHAT IS A LIST COMPREHENSION?
    # [expression for item in list] creates a new list by transforming each item.
    # It's a shortcut for a for loop. Example:
    #   [x * 2 for x in [1, 2, 3]]  →  [2, 4, 6]
    all_symbols = [{"key": sym, "emoji": sym, "image": None, "label": label}
                   for sym, label in WORK_SYMBOLS]

    # Load custom symbols from disk
    symbols_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "symbols")
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
    btn_add_custom.setStyleSheet(INNER_BUTTON_STYLE)
    grid_container_layout.addWidget(btn_add_custom)

    # Toggle button to show/hide the selection grid
    btn_toggle_grid = QPushButton("Symbole ausblenden", content)
    btn_toggle_grid.setStyleSheet(INNER_BUTTON_STYLE)
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

    def on_symbols_resize(event):
        w = content.width()
        h = content.height()
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

    orig_sym_resize = content.resizeEvent
    def sym_resize_wrapper(event):
        if orig_sym_resize:
            orig_sym_resize(event)
        on_symbols_resize(event)
    content.resizeEvent = sym_resize_wrapper

    return panel


# =====================================================================
# NOISE MONITOR PANEL (Lautstärkeanzeige)
# =====================================================================
# Listens to the microphone and displays the current noise level.
# Shows a traffic light (green/yellow/red) that changes based on volume.
# Requires PyQt6-QtMultimedia to be installed (optional dependency).

class CumulativeTrafficLight(QWidget):
    """A traffic light widget with 3 stacked circles (red/yellow/green).
    Drawn with QPainter — another example of custom widget drawing."""
    """A big traffic light widget that paints 3 stacked circles."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._level = "green"  # "green", "yellow", or "red"
        self.setMinimumSize(60, 120)

    def set_level(self, level):
        self._level = level
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        # 3 circles stacked vertically with some padding
        diameter = min(w - 10, (h - 20) // 3)
        if diameter < 10:
            diameter = 10
        x_center = w // 2
        gap = (h - 3 * diameter) // 4

        colors_order = [
            ("red", "#FF4444"),
            ("yellow", "#FFDD00"),
            ("green", "#44DD44"),
        ]
        dim_color = "#333333"

        for i, (name, bright) in enumerate(colors_order):
            y = gap + i * (diameter + gap)
            if self._level == name:
                painter.setBrush(QBrush(QColor(bright)))
            else:
                painter.setBrush(QBrush(QColor(dim_color)))
            painter.setPen(QPen(QColor(255, 255, 255, 60), 2))
            painter.drawEllipse(x_center - diameter // 2, y, diameter, diameter)

        painter.end()


def create_noise_panel():
    panel = FloatingPanel("🔊 Lautstärke-Monitor")
    panel.setMinimumSize(280, 350)

    content = QWidget()
    content.setStyleSheet("background: transparent; border: none;")
    cl = QVBoxLayout(content)
    cl.setContentsMargins(12, 12, 12, 12)
    cl.setSpacing(8)

    # Status label
    status_lbl = QLabel("🔊 Lautstärke-Monitor", content)
    status_lbl.setStyleSheet("color: white; font-size: 15px; font-weight: bold; background: transparent; border: none;")
    status_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
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

    # Threshold slider
    thresh_row = QHBoxLayout()
    thresh_lbl = QLabel("Schwelle:", content)
    thresh_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    thresh_slider = QSlider(Qt.Orientation.Horizontal, content)
    thresh_slider.setRange(10, 90)
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
    cl.addLayout(cum_row)

    # Too loud counter
    counter_row = QHBoxLayout()
    counter_lbl = QLabel("Zu laut:", content)
    counter_lbl.setStyleSheet("color: white; font-size: 13px; background: transparent; border: none;")
    counter_val = QLabel("0", content)
    counter_val.setStyleSheet("color: #FF4444; font-size: 18px; font-weight: bold; background: transparent; border: none;")
    btn_reset_counter = QPushButton("↺ Reset", content)
    btn_reset_counter.setStyleSheet(INNER_BUTTON_STYLE)
    counter_row.addWidget(counter_lbl)
    counter_row.addWidget(counter_val)
    counter_row.addStretch()
    counter_row.addWidget(btn_reset_counter)
    cl.addLayout(counter_row)

    # Start/Stop buttons
    btn_row = QHBoxLayout()
    btn_start = QPushButton("▶ Start", content)
    btn_start.setStyleSheet(INNER_BUTTON_STYLE)
    btn_stop = QPushButton("⏹ Stop", content)
    btn_stop.setStyleSheet(INNER_BUTTON_STYLE)
    btn_row.addWidget(btn_start)
    btn_row.addWidget(btn_stop)
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
    }
    poll_timer = QTimer()
    poll_timer.setInterval(50)

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
        level = min(100, int(rms / 327.67 * 100 / 100 * 100))
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

    def poll():
        level = compute_level()
        level_bar.setValue(level)
        threshold = thresh_slider.value()

        if level < threshold * 0.6:
            emoji = "🟢"
            color = "#44DD44"
        elif level < threshold:
            emoji = "🟡"
            color = "#FFDD00"
        else:
            emoji = "🔴"
            color = "#FF4444"

        level_lbl.setText(f"{emoji} {level}%")
        level_lbl.setStyleSheet(
            f"color: {color}; font-size: 18px; font-weight: bold; "
            f"background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); "
            f"border-radius: 6px; padding: 4px;"
        )

        # Count "too loud" events (only once per spike)
        if level >= threshold:
            if not audio_state["was_loud"]:
                audio_state["too_loud_count"] += 1
                counter_val.setText(str(audio_state["too_loud_count"]))
                audio_state["was_loud"] = True
                update_cumulative_light()
        else:
            audio_state["was_loud"] = False

    poll_timer.timeout.connect(poll)

    def start_monitoring():
        if audio_state["running"]:
            return
        if not HAS_MULTIMEDIA:
            status_lbl.setText("⚠ QtMultimedia nicht verfügbar")
            return
        try:
            fmt = QAudioFormat()
            fmt.setSampleRate(16000)
            fmt.setChannelCount(1)
            fmt.setSampleFormat(QAudioFormat.SampleFormat.Int16)

            device = QMediaDevices.defaultAudioInput()
            if device.isNull():
                status_lbl.setText("⚠ Kein Mikrofon gefunden")
                return

            source = QAudioSource(device, fmt)
            io_device = source.start()
            audio_state["source"] = source
            audio_state["io_device"] = io_device
            audio_state["running"] = True
            poll_timer.start()
            status_lbl.setText("🎤 Aufnahme läuft…")
        except Exception as e:
            status_lbl.setText(f"⚠ Fehler: {e}")

    def stop_monitoring():
        poll_timer.stop()
        if audio_state["source"]:
            audio_state["source"].stop()
            audio_state["source"] = None
            audio_state["io_device"] = None
        audio_state["running"] = False
        level_bar.setValue(0)
        level_lbl.setText("—")
        level_lbl.setStyleSheet(
            "color: #44DD44; font-size: 18px; font-weight: bold; "
            "background: rgba(255,255,255,10); border: 1px solid rgba(255,255,255,30); "
            "border-radius: 6px; padding: 4px;"
        )
        status_lbl.setText("🔊 Lautstärke-Monitor")

    def reset_counter():
        audio_state["too_loud_count"] = 0
        audio_state["cumulative_level"] = "green"
        counter_val.setText("0")
        traffic_light.set_level("green")

    btn_start.clicked.connect(start_monitoring)
    btn_stop.clicked.connect(stop_monitoring)
    btn_reset_counter.clicked.connect(reset_counter)

    # Stop monitoring when panel is closed
    panel.closed.connect(stop_monitoring)

    # Store threshold spinboxes for layout persistence
    panel.noise_spin_yellow = spin_yellow
    panel.noise_spin_red = spin_red

    return panel


# =====================================================================
# QR-CODE GENERATOR PANEL
# =====================================================================
# Type a URL or text and it generates a QR code image that students can
# scan with their phones. Requires the 'qrcode' library (optional).

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
    btn_generate.setStyleSheet(INNER_BUTTON_STYLE)
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
            import io as _io
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
    orig_qr_resize = qr_display.resizeEvent
    def on_qr_resize(event):
        if orig_qr_resize:
            orig_qr_resize(event)
        scale_and_set_pixmap()
    qr_display.resizeEvent = on_qr_resize

    btn_generate.clicked.connect(generate_qr)
    url_input.returnPressed.connect(generate_qr)

    return panel


# =====================================================================
# HELP PANEL (Hilfe)
# =====================================================================
# Shows keyboard shortcuts, tips, and a brief guide for using the app.

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
    scroll.setStyleSheet(f"QScrollArea {{ background: transparent; border: none; }} {SCROLLBAR_STYLE}")

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
        ]),
        ("🖱️ Fenster-Bedienung", [
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
        ("🚦 Ampelsystem", [
            "Klick-Modus: Auf den Punkt klicken um Farbe zu wechseln",
            "Sortier-Modus: Namen per Drag & Drop zwischen Farben verschieben",
            "'Alle auf Grün' setzt alle zurück",
        ]),
        ("🔊 Lautstärke-Monitor", [
            "Misst die Umgebungslautstärke über das Mikrofon",
            "Schwelle per Slider einstellen",
            "Zählt wie oft es 'zu laut' war",
        ]),
        ("💾 Layouts", [
            "Layouts werden automatisch beim Beenden gespeichert",
            "Beim Start wird das letzte Layout wiederhergestellt",
            "Pro Klasse wird ein eigenes Layout gespeichert",
            "Texteditor-Inhalt wird mitgespeichert",
            "Layout-Dateien liegen im 'layouts/' Ordner",
        ]),
        ("⬇ Alles minimieren", [
            "⬇ Button in der Toolbar — alles ausblenden",
            "Blauer ▲ Button erscheint zum Wiederherstellen",
        ]),
    ]

    for section_title, items in help_sections:
        header = QLabel(section_title, inner)
        header.setStyleSheet(
            "color: #4488FF; font-size: 15px; font-weight: bold; "
            "background: transparent; border: none; padding-top: 4px;"
        )
        il.addWidget(header)
        for item in items:
            lbl = QLabel(f"  • {item}", inner)
            lbl.setWordWrap(True)
            lbl.setStyleSheet(
                "color: rgba(255,255,255,200); font-size: 13px; "
                "background: transparent; border: none; padding: 1px 8px;"
            )
            il.addWidget(lbl)

    il.addStretch()
    scroll.setWidget(inner)
    cl.addWidget(scroll)

    panel.set_content_widget(content)
    return panel


# ---------------------------------------------------------------------------
# OverlayBackground – invisible click-through
# ---------------------------------------------------------------------------

class OverlayBackground(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setGeometry(QApplication.primaryScreen().geometry())
        if sys.platform == "win32":
            QTimer.singleShot(0, self._set_click_through)
        quit_app = QApplication.instance().quit
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self).activated.connect(quit_app)
        QShortcut(QKeySequence("Ctrl+Q"), self).activated.connect(quit_app)

    def _set_click_through(self):
        import ctypes
        hwnd = int(self.winId())
        style = ctypes.windll.user32.GetWindowLongW(hwnd, -20)
        ctypes.windll.user32.SetWindowLongW(hwnd, -20, style | 0x00080000 | 0x00000020)

    def paintEvent(self, event):
        p = QPainter(self)
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


def save_layout(panels, toolbar, text_html, traffic_lights, class_name=None, ampel_rules="", noise_thresholds=None):
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


# =====================================================================
# MAIN APPLICATION CONTROLLER
# =====================================================================
# This is the "brain" of the app. It:
#   1. Creates ALL panels (timer, symbols, ampel, etc.)
#   2. Creates the toolbar and connects its buttons to show/hide panels
#   3. Handles loading/saving classes and layouts
#   4. Manages the global minimize/restore feature
#   5. Positions everything on screen
#
# This is NOT a QWidget — it's a plain Python class that owns and
# coordinates all the widgets.

class OverlayApp:
    def __init__(self):
        self.app = QApplication.instance()  # Get the running QApplication
        screen = QApplication.primaryScreen().geometry()  # Screen size
        self._loaded_students = None         # Currently loaded class: (name, [students])
        self._loaded_class_name = None       # Name of the loaded class
        self._loaded_class_filepath = None   # Path to the class JSON file
        self._visible_before_minimize = []   # Remember which panels were open

        # The transparent background layer (click-through)
        self.background = OverlayBackground()

        # The toolbar at the top of the screen
        self.toolbar = OverlayToolbar()
        tw = min(screen.width() - 100, 1400)  # Don't make it wider than 1400px
        self.toolbar.setGeometry((screen.width() - tw) // 2, 8, tw, 42)

        # --- Create all panels and set their initial positions ---
        # setGeometry(x, y, width, height) sets both position and size at once
        self.text_panel = create_text_editor_panel()
        self.text_panel.setGeometry(300, 70, 850, screen.height() - 140)

        self.student_panel = create_student_list_panel()
        self.student_panel.setGeometry(30, 70, 260, screen.height() - 140)

        self.timer_panel = create_timer_panel()
        self.timer_panel.setGeometry(screen.width() - 370, 70, 340, 300)

        self.random_panel = create_random_panel(self._get_students)
        self.random_panel.setGeometry(screen.width() - 400, 400, 360, 450)

        self.traffic_panel = create_traffic_light_panel(self._get_students)
        self.traffic_panel.setGeometry(30, 70, 300, screen.height() - 140)

        self.symbols_panel = create_symbols_panel()
        self.symbols_panel.setGeometry(screen.width() // 2 - 200, screen.height() // 2 - 150, 440, 300)

        self.noise_panel = create_noise_panel()
        self.noise_panel.setGeometry(screen.width() - 350, screen.height() - 350, 320, 300)

        self.qr_panel = create_qr_panel()
        self.qr_panel.setGeometry(screen.width() // 2 - 175, screen.height() // 2 - 200, 350, 400)

        self.help_panel = create_help_panel()
        self.help_panel.setGeometry(screen.width() // 2 - 220, 80, 440, 500)

        # Restore button (hidden initially)
        self.restore_btn = RestoreButton()
        self.restore_btn.setGeometry(screen.width() // 2 - 24, 4, 48, 48)
        self.restore_btn.clicked.connect(self._restore_all)
        self.restore_btn.hide()

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
        self.toolbar.add_panel_button("symbols", "🖼 Symbole",
            lambda checked: self._toggle_panel("symbols", checked), enabled=True)
        self.toolbar.add_panel_button("noise_monitor", "🔊 Lautstärke",
            lambda checked: self._toggle_panel("noise_monitor", checked), enabled=True)
        self.toolbar.add_panel_button("qr_code", "📱 QR-Code",
            lambda checked: self._toggle_panel("qr_code", checked), enabled=True)
        self.toolbar.add_separator()
        self.toolbar.add_panel_button("help", "❓ Hilfe",
            lambda checked: self._toggle_panel("help", checked), enabled=True)

        # Minimize + Quit
        self.toolbar.add_minimize_button(self._minimize_all)
        self.toolbar.add_quit_button(self._quit)

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
            load_students_into_panel(self.student_panel, cn, students)
            if hasattr(self.traffic_panel, 'load_students'):
                self.traffic_panel.load_students(students)
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
        editor.setGeometry(screen.width() // 2 - 220, screen.height() // 2 - 250, 440, 500)
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

        save_layout(
            self._panels,
            self.toolbar,
            text_html,
            traffic_lights,
            self._loaded_class_name,
            ampel_rules,
            noise_thresholds,
        )

    def _apply_layout(self, data):
        """Apply a saved layout."""
        # Toolbar position
        tb = data.get("toolbar", {})
        if tb:
            self.toolbar.move(tb.get("x", self.toolbar.x()), tb.get("y", self.toolbar.y()))
            w = tb.get("width", self.toolbar.width())
            self.toolbar.resize(w, 42)

        # Panels
        panels_data = data.get("panels", {})
        for pid, pdata in panels_data.items():
            panel = self._panels.get(pid)
            if panel:
                panel.setGeometry(
                    pdata.get("x", panel.x()),
                    pdata.get("y", panel.y()),
                    pdata.get("width", panel.width()),
                    pdata.get("height", panel.height()),
                )
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

    def _restore_last_session(self):
        """Restore the last session on startup."""
        last_class = load_last_session_class()

        if last_class:
            # Find the class file
            class_files = discover_class_files()
            for dn, fp in class_files:
                try:
                    cn, _ = load_class_list(fp)
                    if cn == last_class:
                        # Load the class first (without saving current empty state)
                        cn, students = load_class_list(fp)
                        self._loaded_students = (cn, students)
                        self._loaded_class_name = cn
                        self._loaded_class_filepath = fp
                        load_students_into_panel(self.student_panel, cn, students)
                        if hasattr(self.traffic_panel, 'load_students'):
                            self.traffic_panel.load_students(students)
                        break
                except Exception:
                    pass

        # Load layout (class-specific or default)
        layout_data = load_layout(last_class)
        if layout_data:
            self._apply_layout(layout_data)

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
        self.toolbar.show()
        self.toolbar.raise_()
        for pid in self._visible_before_minimize:
            panel = self._panels.get(pid)
            if panel:
                panel.show()
                panel.raise_()
                self.toolbar.set_button_checked(pid, True)
        self._visible_before_minimize = []

    def _quit(self):
        """Save layout and quit."""
        self._save_current_layout()
        self.app.quit()

    def show(self):
        self.background.show()
        self.toolbar.show()
        self.text_panel.show()
        self.student_panel.show()


# =====================================================================
# ENTRY POINT — WHERE THE PROGRAM STARTS
# =====================================================================
# When you run "python overlay.py", Python executes everything from top
# to bottom. Class/function definitions are just registered, not run.
# The actual execution starts at the "if __name__ == '__main__'" block
# at the very bottom, which calls main().

def main():
    # Handle high-DPI displays (e.g. 4K monitors) properly
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    # Create the Qt application — every Qt program needs exactly one of these
    app = QApplication(sys.argv)
    # Create and show our overlay
    overlay = OverlayApp()
    overlay.show()
    # app.exec() starts Qt's event loop — it keeps the app running and
    # processing user input (clicks, keyboard, timers, etc.) until you quit.
    # sys.exit() ensures a clean exit with the right return code.
    sys.exit(app.exec())


# This is the standard Python entry point check.
# __name__ == "__main__" is True only when you run this file directly
# (not when it's imported as a module by another file).
if __name__ == "__main__":
    main()
