"""关于窗口。"""

from __future__ import annotations

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout

from .. import paths
from .mobius import make_logo


class AboutDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("关于")
        self.setFixedWidth(420)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        logo = QLabel()
        logo.setPixmap(make_logo(96))
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(logo)

        name = QLabel(paths.APP_NAME)
        name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(name)

        version = QLabel(f"版本 {paths.APP_VERSION}")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version)

        license_label = QLabel(f"开源许可证：{paths.APP_LICENSE}")
        license_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(license_label)

        link_btn = QPushButton(paths.GITHUB_REPO)
        link_btn.setFlat(True)
        link_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        link_btn.setStyleSheet("color: #7b8cff;")
        link_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(paths.GITHUB_REPO)))
        layout.addWidget(link_btn)

        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)