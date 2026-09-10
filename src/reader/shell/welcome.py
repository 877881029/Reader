from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPen
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

PAPER = QColor("#f4efe6")
INK = QColor("#1c1915")
COBALT = QColor("#2563eb")
RULE = QColor(37, 99, 235, 36)
GHOST = QColor(37, 99, 235, 16)

_BADGE_BY_SUFFIX = {
    ".md": "MD",
    ".pdf": "PDF",
    ".pptx": "PPT",
    ".docx": "DOC",
    ".xlsx": "XLS",
}


class _ElideLabel(QLabel):
    def __init__(self, full_text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._full_text = full_text
        self.setToolTip(full_text)
        self.setText(full_text)
        self.setWordWrap(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.setMinimumWidth(32)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._elide()

    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._elide()

    def _elide(self) -> None:
        self.setText(
            self.fontMetrics().elidedText(
                self._full_text,
                Qt.TextElideMode.ElideMiddle,
                max(self.width(), 32),
            )
        )


class _RecentRow(QWidget):
    def __init__(self, path: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
        self.setObjectName("welcomeRecentRow")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 10, 14, 10)
        layout.setSpacing(12)

        badge = QLabel(_BADGE_BY_SUFFIX.get(path.suffix.lower(), path.suffix.lstrip(".").upper()[:3] or "FILE"))
        badge.setObjectName("welcomeRecentBadge")
        badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        badge.setFixedSize(40, 40)
        badge.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        layout.addWidget(badge, 0, Qt.AlignmentFlag.AlignVCenter)

        copy = QVBoxLayout()
        copy.setContentsMargins(0, 0, 0, 0)
        copy.setSpacing(2)
        name = QLabel(path.name)
        name.setObjectName("welcomeRecentName")
        name.setToolTip(path.name)
        name.setWordWrap(False)
        name.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        location = _ElideLabel(str(path))
        location.setObjectName("welcomeRecentPath")
        location.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        copy.addWidget(name)
        copy.addWidget(location)
        layout.addLayout(copy, 1)

    def sizeHint(self) -> QSize:
        return QSize(320, 62)


class WelcomePage(QWidget):
    open_requested = Signal()
    new_markdown_requested = Signal()
    recent_opened = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("welcomePage")
        self.setAcceptDrops(True)
        self.setAutoFillBackground(False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet(
            """
            QWidget#welcomePage {
                background: transparent;
            }
            QWidget#welcomeBrandColumn,
            QWidget#welcomeRecentColumn {
                background: transparent;
            }
            QFrame#welcomeAccent {
                background: #2563eb;
                border: none;
                border-radius: 2px;
            }
            QLabel#welcomeBrand {
                color: #1c1915;
                font-family: "Palatino Linotype", "Book Antiqua", "Georgia", serif;
                font-size: 46px;
                font-weight: 600;
                letter-spacing: -0.5px;
            }
            QLabel#welcomeVersion {
                color: #8a8176;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 11px;
                letter-spacing: 2px;
            }
            QPushButton#welcomeOpenButton {
                background: #2563eb;
                border: none;
                border-radius: 8px;
                color: #f7f4ee;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 14px;
                font-weight: 600;
                padding: 9px 18px;
                min-width: 168px;
                min-height: 36px;
            }
            QPushButton#welcomeOpenButton:hover {
                background: #1d4ed8;
            }
            QPushButton#welcomeOpenButton:pressed {
                background: #1e40af;
            }
            QPushButton#welcomeNewButton {
                background: transparent;
                border: 1px solid #2563eb;
                border-radius: 8px;
                color: #2563eb;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 14px;
                padding: 8px 18px;
                min-width: 168px;
                min-height: 36px;
            }
            QPushButton#welcomeNewButton:hover {
                background: rgba(37, 99, 235, 0.08);
            }
            QLabel#emptyWindowHint {
                color: #9a9186;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 12px;
            }
            QLabel#welcomeRecentHeading {
                color: #3f3a34;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 12px;
                font-weight: 600;
                letter-spacing: 1.4px;
            }
            QLabel#welcomeRecentEmpty {
                color: #9a9186;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 12px;
            }
            QListWidget#welcomeRecentList {
                background: transparent;
                border: none;
                outline: none;
                padding: 0px;
            }
            QListWidget#welcomeRecentList::item {
                background: #fffaf2;
                border: 1px solid #e4d9c7;
                border-radius: 10px;
                color: transparent;
                margin-bottom: 8px;
            }
            QListWidget#welcomeRecentList::item:hover {
                background: #fff6e8;
                border: 1px solid #d7c4a6;
            }
            QListWidget#welcomeRecentList::item:selected {
                background: #eaf0ff;
                border: 1px solid #2563eb;
            }
            QLabel#welcomeRecentBadge {
                background: #2563eb;
                border-radius: 8px;
                color: #f7f4ee;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 10px;
                font-weight: 700;
                letter-spacing: 0.8px;
            }
            QLabel#welcomeRecentName {
                color: #1c1915;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 14px;
                font-weight: 600;
            }
            QLabel#welcomeRecentPath {
                color: #8a8176;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 11px;
            }
            """
        )

        root = QHBoxLayout(self)
        root.setContentsMargins(72, 56, 56, 48)
        root.setSpacing(56)

        left = QWidget(self)
        left.setObjectName("welcomeBrandColumn")
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        brand_row = QHBoxLayout()
        brand_row.setSpacing(16)
        accent = QFrame(left)
        accent.setObjectName("welcomeAccent")
        accent.setFixedWidth(5)
        accent.setFixedHeight(58)
        brand_row.addWidget(accent, 0, Qt.AlignmentFlag.AlignTop)
        brand_copy = QVBoxLayout()
        brand_copy.setSpacing(6)
        brand = QLabel("Reader")
        brand.setObjectName("welcomeBrand")
        version = QLabel(f"VERSION {product_version()}")
        version.setObjectName("welcomeVersion")
        brand_copy.addWidget(brand)
        brand_copy.addWidget(version)
        brand_row.addLayout(brand_copy, 1)
        left_layout.addLayout(brand_row)
        left_layout.addSpacing(32)

        open_button = QPushButton("打开文件")
        open_button.setObjectName("welcomeOpenButton")
        open_button.setCursor(Qt.CursorShape.PointingHandCursor)
        open_button.clicked.connect(self.open_requested.emit)
        left_layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignLeft)

        left_layout.addSpacing(10)
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
        right.setObjectName("welcomeRecentColumn")
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 10, 0, 0)
        right_layout.setSpacing(12)
        heading = QLabel("最近打开")
        heading.setObjectName("welcomeRecentHeading")
        right_layout.addWidget(heading)
        self._recent_empty = QLabel("还没有最近打开的文件")
        self._recent_empty.setObjectName("welcomeRecentEmpty")
        right_layout.addWidget(self._recent_empty)
        self._recent = QListWidget()
        self._recent.setObjectName("welcomeRecentList")
        self._recent.setWordWrap(False)
        self._recent.setSpacing(0)
        self._recent.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._recent.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._recent.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._recent.itemClicked.connect(self._emit_recent)
        right_layout.addWidget(self._recent, 1)
        root.addWidget(right, 1)

        self.reload_recent()

    def paintEvent(self, event) -> None:  # noqa: N802 - Qt API
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), PAPER)
        ghost = QFont("Palatino Linotype", 220, QFont.Weight.Bold)
        painter.setFont(ghost)
        painter.setPen(GHOST)
        painter.drawText(self.rect().adjusted(18, -12, 0, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop, "R")
        column = self.findChild(QWidget, "welcomeRecentColumn")
        if column is not None and column.x() > 40:
            x = column.x() - 28
            painter.setPen(QPen(RULE, 1))
            painter.drawLine(x, 64, x, self.height() - 48)
        painter.end()
        super().paintEvent(event)

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
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, str(path))
            item.setToolTip(str(path))
            row = _RecentRow(path)
            item.setSizeHint(row.sizeHint())
            self._recent.addItem(item)
            self._recent.setItemWidget(item, row)
