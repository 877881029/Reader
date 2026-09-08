from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from reader.shell.recent import visible_recent
from reader.version import product_version


class WelcomePage(QWidget):
    open_requested = Signal()
    new_markdown_requested = Signal()
    recent_opened = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("welcomePage")
        self.setAcceptDrops(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            """
            QWidget#welcomePage {
                background: #f9f9f9;
            }
            QFrame#welcomeAccent {
                background: #1a4fbf;
                border: none;
            }
            QLabel#welcomeBrand {
                color: #1b1b1b;
                font-family: "Palatino Linotype", "Georgia", serif;
                font-size: 44px;
                font-weight: 600;
            }
            QLabel#welcomeVersion {
                color: #6f6f6f;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
                letter-spacing: 1px;
            }
            QPushButton#welcomeOpenButton,
            QPushButton#welcomeNewButton {
                background: transparent;
                border: none;
                border-bottom: 1px solid #d4d4d4;
                color: #1a4fbf;
                font-family: "Segoe UI", sans-serif;
                font-size: 15px;
                padding: 10px 0 8px 0;
                text-align: left;
            }
            QPushButton#welcomeOpenButton:hover,
            QPushButton#welcomeNewButton:hover {
                border-bottom: 1px solid #1a4fbf;
            }
            QLabel#emptyWindowHint {
                color: #8a8a8a;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
            }
            QLabel#welcomeRecentHeading {
                color: #3d3d3d;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
                font-weight: 600;
            }
            QLabel#welcomeRecentEmpty {
                color: #8a8a8a;
                font-family: "Segoe UI", sans-serif;
                font-size: 12px;
            }
            QListWidget#welcomeRecentList {
                background: transparent;
                border: none;
                color: #222;
                font-family: "Segoe UI", sans-serif;
                font-size: 13px;
                outline: none;
            }
            QListWidget#welcomeRecentList::item {
                padding: 10px 8px;
                border-radius: 6px;
            }
            QListWidget#welcomeRecentList::item:hover {
                background: #efefef;
            }
            QListWidget#welcomeRecentList::item:selected {
                background: #e6ecf8;
                color: #1b1b1b;
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(72, 56, 56, 48)
        root.setSpacing(48)

        left = QWidget(self)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(14)
        accent = QFrame(left)
        accent.setObjectName("welcomeAccent")
        accent.setFixedWidth(4)
        accent.setFixedHeight(52)
        brand_row.addWidget(accent, 0, Qt.AlignmentFlag.AlignTop)
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(4)
        brand = QLabel("Reader")
        brand.setObjectName("welcomeBrand")
        version = QLabel(f"VERSION {product_version()}")
        version.setObjectName("welcomeVersion")
        brand_copy.addWidget(brand)
        brand_copy.addWidget(version)
        brand_row.addLayout(brand_copy, 1)
        left_layout.addLayout(brand_row)
        left_layout.addSpacing(28)

        open_button = QPushButton("打开文件")
        open_button.setObjectName("welcomeOpenButton")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(self.open_requested.emit)
        left_layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignLeft)

        new_button = QPushButton("新建 Markdown")
        new_button.setObjectName("welcomeNewButton")
        new_button.setCursor(Qt.CursorShape.PointingHandCursor)
        new_button.clicked.connect(self.new_markdown_requested.emit)
        left_layout.addWidget(new_button, 0, Qt.AlignmentFlag.AlignLeft)

        left_layout.addSpacing(28)
        hint = QLabel("拖入文件，或按 Ctrl+O 打开")
        hint.setObjectName("emptyWindowHint")
        left_layout.addWidget(hint)
        left_layout.addStretch(1)
        root.addWidget(left, 1)

        right = QWidget(self)
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 8, 0, 0)
        right_layout.setSpacing(10)
        heading = QLabel("最近打开")
        heading.setObjectName("welcomeRecentHeading")
        right_layout.addWidget(heading)
        self._recent_empty = QLabel("还没有最近打开的文件")
        self._recent_empty.setObjectName("welcomeRecentEmpty")
        right_layout.addWidget(self._recent_empty)
        self._recent = QListWidget()
        self._recent.setObjectName("welcomeRecentList")
        self._recent.setWordWrap(True)
        self._recent.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._recent.itemClicked.connect(self._emit_recent)
        right_layout.addWidget(self._recent, 1)
        root.addWidget(right, 1)

        self.reload_recent()

    def _emit_recent(self, item: QListWidgetItem) -> None:
        path = item.data(Qt.ItemDataRole.UserRole)
        if path:
            self.recent_opened.emit(str(path))

    def reload_recent(self) -> None:
        self._recent.clear()
        paths = visible_recent()
        self._recent_empty.setVisible(not paths)
        self._recent.setVisible(bool(paths))
        for path in paths:
            item = QListWidgetItem(f"{path.name}\n{path}")
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            self._recent.addItem(item)
