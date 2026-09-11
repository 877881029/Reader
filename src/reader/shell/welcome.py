from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from reader.shell.recent import visible_recent
from reader.sniff import SUPPORTED_EXTENSIONS
from reader.theme import PAPER as PAPER_HEX
from reader.version import product_version

PAPER = QColor(PAPER_HEX)
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
    ".json": "JSON",
    ".yaml": "YAML",
    ".yml": "YAML",
    ".xml": "XML",
    ".c": "C",
    ".h": "H",
    ".svg": "SVG",
    ".png": "PNG",
    ".jpg": "JPG",
    ".jpeg": "JPG",
    ".gif": "GIF",
    ".webp": "WEBP",
    ".bmp": "BMP",
}


def parse_lookup_path(text: str) -> Path:
    stripped = text.strip().strip('"').strip("'").strip()
    return Path(stripped).expanduser()


def openable_in_directory(path: Path) -> list[Path]:
    try:
        if not path.is_dir():
            return []
        folders: list[Path] = []
        files: list[Path] = []
        for child in path.iterdir():
            try:
                if child.name.startswith("."):
                    continue
                if child.is_dir():
                    folders.append(child)
                elif child.is_file() and child.suffix.lower() in SUPPORTED_EXTENSIONS:
                    files.append(child)
            except OSError:
                continue
        folders.sort(key=lambda item: item.name.lower())
        files.sort(key=lambda item: item.name.lower())
        return folders + files
    except OSError:
        return []


def _badge_text(path: Path) -> str:
    try:
        if path.is_dir():
            return "DIR"
    except OSError:
        pass
    return _BADGE_BY_SUFFIX.get(
        path.suffix.lower(),
        path.suffix.lstrip(".").upper()[:3] or "FILE",
    )


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

        badge = QLabel(_badge_text(path))
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
            QLineEdit#welcomeLookup {
                background: #fffaf2;
                color: #1c1915;
                border: 1px solid #e4d9c7;
                border-radius: 8px;
                padding: 4px 8px;
                font-family: "Candara", "Calibri", "Segoe UI", sans-serif;
                font-size: 12px;
                min-height: 24px;
            }
            QLineEdit#welcomeLookup:focus {
                border: 1px solid #2563eb;
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
        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading_row.setSpacing(12)
        heading = QLabel("最近打开")
        heading.setObjectName("welcomeRecentHeading")
        heading.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)
        self._lookup = QLineEdit()
        self._lookup.setObjectName("welcomeLookup")
        self._lookup.setPlaceholderText("路径")
        self._lookup.setClearButtonEnabled(False)
        self._lookup.hide()
        self._lookup.returnPressed.connect(self._submit_lookup)
        self._lookup.installEventFilter(self)
        heading_row.addWidget(heading, 0, Qt.AlignmentFlag.AlignVCenter)
        heading_row.addWidget(self._lookup, 1)
        right_layout.addLayout(heading_row)
        self._listing_directory = False
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

    def eventFilter(self, watched, event: QEvent) -> bool:  # noqa: N802
        if (
            watched is self._lookup
            and event.type() == QEvent.Type.KeyPress
            and isinstance(event, QKeyEvent)
            and event.key() == Qt.Key.Key_Escape
        ):
            self.hide_lookup()
            return True
        return super().eventFilter(watched, event)

    def show_lookup(self) -> None:
        self._lookup.show()
        self._lookup.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self._lookup.selectAll()

    def hide_lookup(self) -> None:
        was_open = self._lookup.isVisible() or self._listing_directory
        self._lookup.hide()
        self._lookup.clear()
        self._listing_directory = False
        if was_open:
            self.reload_recent()

    def _submit_lookup(self) -> None:
        raw = self._lookup.text()
        if not raw.strip().strip('"').strip("'"):
            self._listing_directory = False
            self.reload_recent()
            return
        path = parse_lookup_path(raw)
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        if resolved.is_file():
            self.recent_opened.emit(str(resolved))
            return
        if resolved.is_dir():
            self._enter_directory(resolved)
            return
        self._listing_directory = True
        self._fill_list([], empty_text="没有可打开的文件")

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

    def _enter_directory(self, path: Path) -> None:
        try:
            resolved = path.resolve()
        except OSError:
            resolved = path
        self._listing_directory = True
        self._lookup.show()
        self._lookup.setText(str(resolved))
        listed = openable_in_directory(resolved) if resolved.is_dir() else []
        self._fill_list(listed, empty_text="没有可打开的文件")

    def _emit_recent(self, item: QListWidgetItem) -> None:
        raw = item.data(Qt.ItemDataRole.UserRole)
        if not raw:
            return
        path = Path(raw)
        try:
            is_dir = path.is_dir()
        except OSError:
            is_dir = False
        if self._listing_directory and is_dir:
            self._enter_directory(path)
            return
        self.recent_opened.emit(str(path))

    def reload_recent(self) -> None:
        self._listing_directory = False
        self._fill_list(visible_recent(), empty_text="还没有最近打开的文件")

    def _fill_list(self, paths: list[Path], *, empty_text: str) -> None:
        self._recent.clear()
        self._recent_empty.setText(empty_text)
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
