# main.py
import os
import sys
from pathlib import Path

# Silence harmless Qt6 Wayland textinput debug warnings on Hyprland / Arch
os.environ["QT_LOGGING_RULES"] = "qt.qpa.wayland.textinput=false"

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

from backend import EqualizerBackend

def main():
    QQuickStyle.setStyle("Basic")

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()

    backend = EqualizerBackend()
    engine.rootContext().setContextProperty("backend", backend)

    qml_file = Path(__file__).resolve().parent / "ui.qml"
    engine.load(os.fspath(qml_file))

    if not engine.rootObjects():
        sys.exit(-1)

    exit_code = app.exec()
    del engine
    sys.exit(exit_code)

if __name__ == "__main__":
    main()
