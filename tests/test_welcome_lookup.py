from pathlib import Path

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget, QWidget

from reader.preview.result import PreviewResult
from reader.shell.recent import remember_recent
from reader.shell.window import MainWindow
from reader.theme import CARD, INK, LINE


def _window() -> MainWindow:
    return MainWindow(
        preview_fn=lambda *_args, **_kwargs: PreviewResult(
            html="<p>ready</p>",
            status_label="内置预览",
        )
    )


def test_openable_in_directory_lists_supported_files_only(tmp_path: Path):
    from reader.shell.welcome import openable_in_directory

    (tmp_path / "keep.md").write_text("x", encoding="utf-8")
    (tmp_path / "skip.exe").write_bytes(b"x")
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "nested.md").write_text("x", encoding="utf-8")
    names = [path.name for path in openable_in_directory(tmp_path)]
    assert names == ["keep.md"]


def test_ctrl_f_shows_hidden_lookup_on_recent_row(qtbot):
    window = _window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)

    lookup = window.findChild(QLineEdit, "welcomeLookup")
    heading = window.findChild(QLabel, "welcomeRecentHeading")
    page = window.findChild(QWidget, "welcomePage")
    hint = window.findChild(QLabel, "emptyWindowHint")
    left = window.findChild(QWidget, "welcomeBrandColumn")
    right = window.findChild(QWidget, "welcomeRecentColumn")
    assert lookup is not None
    assert heading is not None
    assert page is not None
    assert lookup.isVisible() is False
    window.actionFind.trigger()
    assert window.find_bar().isVisible() is False
    assert lookup.isVisible() is True
    assert heading.text() == "最近打开"
    lookup_y = lookup.mapTo(page, QPoint(0, 0)).y()
    heading_y = heading.mapTo(page, QPoint(0, 0)).y()
    assert abs(lookup_y - heading_y) <= 12
    assert hint is not None and "Ctrl+O" in hint.text()
    assert left is not None and right is not None
    assert left.mapTo(page, left.rect().topLeft()).x() < right.mapTo(
        page, right.rect().topLeft()
    ).x()
    sheet = page.styleSheet().replace(" ", "").lower()
    assert CARD.lower() in sheet
    assert LINE.lower() in sheet
    assert INK.lower() in sheet


def test_enter_directory_lists_files_like_recents(qtbot, tmp_path: Path):
    (tmp_path / "note.md").write_text("hello", encoding="utf-8")
    (tmp_path / "skip.bin").write_bytes(b"x")
    window = _window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.actionFind.trigger()
    lookup = window.findChild(QLineEdit, "welcomeLookup")
    assert lookup is not None
    lookup.setText(str(tmp_path))
    qtbot.keyClick(lookup, Qt.Key.Key_Return)

    recent_list = window.findChild(QListWidget, "welcomeRecentList")
    assert recent_list is not None
    assert recent_list.count() == 1
    row = recent_list.itemWidget(recent_list.item(0))
    assert row is not None
    name = row.findChild(QLabel, "welcomeRecentName")
    path_label = row.findChild(QLabel, "welcomeRecentPath")
    assert name is not None and name.text() == "note.md"
    assert path_label is not None
    assert "note.md" in path_label.toolTip()


def test_enter_file_opens_it(qtbot, tmp_path: Path):
    path = tmp_path / "doc.md"
    path.write_text("body", encoding="utf-8")
    window = _window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.actionFind.trigger()
    lookup = window.findChild(QLineEdit, "welcomeLookup")
    assert lookup is not None
    lookup.setText(f'"{path}"')
    qtbot.keyClick(lookup, Qt.Key.Key_Return)
    qtbot.waitUntil(lambda: window.tab_count() == 1)
    assert "doc.md" in window.tab_title(0)


def test_escape_hides_lookup_and_restores_recents(qtbot, tmp_path: Path):
    recent = tmp_path / "saved.md"
    recent.write_text("keep", encoding="utf-8")
    remember_recent(recent)
    folder = tmp_path / "other"
    folder.mkdir()
    (folder / "listed.md").write_text("x", encoding="utf-8")

    window = _window()
    qtbot.addWidget(window)
    window.show()
    qtbot.waitExposed(window)
    window.actionFind.trigger()
    lookup = window.findChild(QLineEdit, "welcomeLookup")
    recent_list = window.findChild(QListWidget, "welcomeRecentList")
    assert lookup is not None and recent_list is not None
    lookup.setText(str(folder))
    qtbot.keyClick(lookup, Qt.Key.Key_Return)
    assert recent_list.count() == 1
    assert recent_list.itemWidget(recent_list.item(0)).findChild(
        QLabel, "welcomeRecentName"
    ).text() == "listed.md"

    qtbot.keyClick(lookup, Qt.Key.Key_Escape)
    assert lookup.isVisible() is False
    assert recent_list.count() == 1
    assert recent_list.itemWidget(recent_list.item(0)).findChild(
        QLabel, "welcomeRecentName"
    ).text() == "saved.md"
