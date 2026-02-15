import sys
import os
import json
import threading
import time

from PyQt6.QtWidgets import *
from PyQt6.QtCore import *
from PyQt6.QtGui import *

from pynput.mouse import Button, Controller
from pynput import keyboard, mouse
from PIL import Image


# ---------------- Paths ---------------- #

APP_DIR = os.path.dirname(os.path.abspath(sys.argv[0]))
CONFIG_PATH = os.path.join(APP_DIR, "config.json")

def resource_path(path):
    try:
        base = sys._MEIPASS
    except:
        base = APP_DIR
    return os.path.join(base, path)


# ---------------- Mouse ---------------- #

mouse_controller = Controller()


# ---------------- Glass Widgets ---------------- #

class GlassButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setStyleSheet("""
        QPushButton {
            background: rgba(255,255,255,120);
            border-radius: 18px;
            color: black;
            font-size: 14px;
            padding: 10px;
        }
        QPushButton:hover { background: rgba(255,255,255,170); }
        QPushButton:pressed { background: rgba(255,255,255,210); }
        """)


class GlassInput(QLineEdit):
    def __init__(self, placeholder):
        super().__init__()
        self.setPlaceholderText(placeholder)
        self.setFixedWidth(80)
        self.setStyleSheet("""
        QLineEdit {
            background: rgba(255,255,255,120);
            border-radius: 14px;
            padding: 6px;
            border: none;
            font-size: 14px;
        }
        """)


# ---------------- Main App ---------------- #

class AutoClicker(QMainWindow):

    def __init__(self):
        super().__init__()

        icon = QIcon(resource_path("icon.ico"))
        self.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)

        self.setWindowTitle("AutoClicker")
        self.setMinimumSize(600, 400)

        self.bg_image = None
        self.bg_path = ""

        self.running = False
        self.waiting = False

        self.click_button = Button.left
        self.hotkey = "f6"

        # Faster but safe resize updates
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.update_background)

        self.init_ui()
        self.load_settings()

        QTimer.singleShot(300, self.start_hotkey_listener)


    # ---------------- UI ---------------- #

    def init_ui(self):

        self.central = QWidget()
        self.setCentralWidget(self.central)

        layout = QVBoxLayout(self.central)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        top = QHBoxLayout()

        self.bg_btn = GlassButton("Change Background")
        self.bg_btn.clicked.connect(self.load_background)

        self.hotkey_btn = GlassButton("Hotkey: f6")
        self.hotkey_btn.clicked.connect(self.set_hotkey)

        top.addWidget(self.bg_btn)
        top.addWidget(self.hotkey_btn)
        layout.addLayout(top)

        clicks = QHBoxLayout()
        self.left_btn = GlassButton("Left Click")
        self.right_btn = GlassButton("Right Click")
        self.left_btn.clicked.connect(lambda: self.set_click(Button.left))
        self.right_btn.clicked.connect(lambda: self.set_click(Button.right))
        clicks.addWidget(self.left_btn)
        clicks.addWidget(self.right_btn)
        layout.addLayout(clicks)

        times = QHBoxLayout()
        self.h_input = GlassInput("Hours")
        self.m_input = GlassInput("Minutes")
        self.s_input = GlassInput("Seconds")
        self.ms_input = GlassInput("Ms")
        times.addWidget(self.h_input)
        times.addWidget(self.m_input)
        times.addWidget(self.s_input)
        times.addWidget(self.ms_input)
        layout.addLayout(times)

        self.start_btn = GlassButton("Start")
        self.start_btn.clicked.connect(self.toggle)
        layout.addWidget(self.start_btn)

        layout.addStretch()


    # ---------------- Config ---------------- #

    def load_settings(self):

        if not os.path.exists(CONFIG_PATH):
            return

        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                cfg = json.load(f)
        except:
            return

        self.hotkey = cfg.get("hotkey", "f6")
        self.h_input.setText(cfg.get("h", ""))
        self.m_input.setText(cfg.get("m", ""))
        self.s_input.setText(cfg.get("s", ""))
        self.ms_input.setText(cfg.get("ms", ""))

        # Restore window size
        w = cfg.get("win_w")
        h = cfg.get("win_h")
        if isinstance(w, int) and isinstance(h, int):
            self.resize(w, h)

        self.set_click(Button.right if cfg.get("click") == "right" else Button.left)

        bg = cfg.get("bg", "")
        if bg and os.path.exists(bg):
            self.bg_path = bg
            self.bg_image = Image.open(bg)
            self.update_background()

        self.hotkey_btn.setText(f"Hotkey: {self.hotkey}")


    def save_settings(self):

        size = self.size()

        cfg = {
            "hotkey": self.hotkey,
            "h": self.h_input.text(),
            "m": self.m_input.text(),
            "s": self.s_input.text(),
            "ms": self.ms_input.text(),
            "click": "right" if self.click_button == Button.right else "left",
            "bg": self.bg_path,
            "win_w": size.width(),
            "win_h": size.height()
        }

        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)


    def closeEvent(self, event):
        self.save_settings()
        event.accept()


    # ---------------- Background ---------------- #

    def load_background(self):

        path, _ = QFileDialog.getOpenFileName(
            self, "Select Image", "", "Images (*.png *.jpg *.jpeg)"
        )

        if path:
            self.bg_path = path
            self.bg_image = Image.open(path)
            self.update_background()


    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resize_timer.start(30)  # smoother updates


    def update_background(self):

        if not self.bg_image:
            return

        w = max(self.width(), 1)
        h = max(self.height(), 1)

        img = self.bg_image.resize((w, h), Image.LANCZOS).convert("RGB")
        data = img.tobytes()
        bytes_per_line = w * 3

        qimg = QImage(
            data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        ).copy()

        pix = QPixmap.fromImage(qimg)

        pal = QPalette()
        pal.setBrush(QPalette.ColorRole.Window, QBrush(pix))
        self.central.setAutoFillBackground(True)
        self.central.setPalette(pal)


    # ---------------- Click Logic ---------------- #

    def set_click(self, btn):

        self.click_button = btn

        if btn == Button.left:
            self.left_btn.setText("Left ✔")
            self.right_btn.setText("Right Click")
        else:
            self.right_btn.setText("Right ✔")
            self.left_btn.setText("Left Click")


    def get_delay(self):

        def num(x): return int(x) if x.isdigit() else 0

        h = num(self.h_input.text())
        m = num(self.m_input.text())
        s = num(self.s_input.text())
        ms = num(self.ms_input.text())

        return max(h * 3600 + m * 60 + s + ms / 1000, 0.001)


    def toggle(self):

        self.running = not self.running
        self.start_btn.setText("Stop" if self.running else "Start")

        if self.running:
            threading.Thread(target=self.run_clicker, daemon=True).start()


    def run_clicker(self):

        while self.running:
            mouse_controller.click(self.click_button)
            time.sleep(self.get_delay())


    # ---------------- Hotkeys ---------------- #

    def set_hotkey(self):

        if self.waiting:
            return

        self.waiting = True
        self.hotkey_btn.setText("Press any key or mouse button...")


    def start_hotkey_listener(self):

        def on_press(key):
            name = str(key).replace("Key.", "")
            if self.waiting:
                self.hotkey = name
                self.waiting = False
                self.hotkey_btn.setText(f"Hotkey: {self.hotkey}")
            elif name == self.hotkey:
                self.toggle()

        def on_click(x, y, button, pressed):
            if not pressed:
                return
            btn = str(button)
            if self.waiting:
                self.hotkey = btn
                self.waiting = False
                self.hotkey_btn.setText(f"Hotkey: {self.hotkey}")
            elif btn == self.hotkey:
                self.toggle()

        keyboard.Listener(on_press=on_press).start()
        mouse.Listener(on_click=on_click).start()


# ---------------- Run ---------------- #

if __name__ == "__main__":

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    win = AutoClicker()
    win.show()

    sys.exit(app.exec())
