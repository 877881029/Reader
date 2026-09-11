from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat, QTextDocument

from reader.theme import COBALT, INK, MUTED

_STRING = "#0f766e"
_NUMBER = "#c2410c"
_LITERAL = "#7c3aed"


def _format(color: str, *, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    fmt = QTextCharFormat()
    fmt.setForeground(QColor(color))
    if bold:
        fmt.setFontWeight(QFont.Weight.DemiBold)
    if italic:
        fmt.setFontItalic(True)
    return fmt


class JsonHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument | None = None) -> None:
        super().__init__(parent)
        self._rules = [
            (QRegularExpression(r"\b(?:true|false|null)\b"), _format(_LITERAL, bold=True)),
            (QRegularExpression(r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b"), _format(_NUMBER)),
            (QRegularExpression(r"[{}\[\],:]"), _format(INK)),
            (QRegularExpression(r'"(?:\\.|[^"\\])*"'), _format(_STRING)),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, fmt in self._rules:
            match = pattern.globalMatch(text)
            while match.hasNext():
                captured = match.next()
                self.setFormat(captured.capturedStart(), captured.capturedLength(), fmt)


class YamlHighlighter(QSyntaxHighlighter):
    def __init__(self, parent: QTextDocument | None = None) -> None:
        super().__init__(parent)
        self._comment = QRegularExpression(r"#.*$")
        self._key = QRegularExpression(r"^(\s*)([^:#\s][^:]*)(:)(?=\s|$)")
        self._string = QRegularExpression(r"(?:'(?:\\.|[^'\\])*'|\"(?:\\.|[^\"\\])*\")")
        self._literal = QRegularExpression(
            r"\b(?:true|false|null|True|False|Null|yes|no|on|off)\b"
        )
        self._number = QRegularExpression(r"-?\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b")
        self._list = QRegularExpression(r"^(\s*)(-)(?=\s)")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        self._apply(text, self._number, _format(_NUMBER))
        self._apply(text, self._literal, _format(_LITERAL, bold=True))
        self._apply(text, self._string, _format(_STRING))
        match = self._list.match(text)
        if match.hasMatch():
            self.setFormat(match.capturedStart(2), match.capturedLength(2), _format(COBALT, bold=True))
        key = self._key.match(text)
        if key.hasMatch():
            self.setFormat(key.capturedStart(2), key.capturedLength(2), _format(COBALT, bold=True))
        self._apply(text, self._comment, _format(MUTED, italic=True))

    def _apply(self, text: str, pattern: QRegularExpression, fmt: QTextCharFormat) -> None:
        match = pattern.globalMatch(text)
        while match.hasNext():
            captured = match.next()
            self.setFormat(captured.capturedStart(), captured.capturedLength(), fmt)


class XmlHighlighter(QSyntaxHighlighter):
    StateNormal = 0
    StateComment = 1

    def __init__(self, parent: QTextDocument | None = None) -> None:
        super().__init__(parent)
        self._comment_start = QRegularExpression(r"<!--")
        self._comment_end = QRegularExpression(r"-->")
        self._tag = QRegularExpression(r"</?[\w:.-]+|/?\s*>")
        self._attr = QRegularExpression(r"\b[\w:.-]+(?=\s*=)")
        self._string = QRegularExpression(r"(?:\"[^\"]*\"|'[^']*')")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.StateComment:
            end = self._comment_end.match(text)
            if end.hasMatch():
                close_at = end.capturedStart() + end.capturedLength()
                self.setFormat(0, close_at, _format(MUTED, italic=True))
                self.setCurrentBlockState(self.StateNormal)
                rest = text[close_at:]
                self._highlight_markup(rest, close_at)
            else:
                self.setFormat(0, len(text), _format(MUTED, italic=True))
                self.setCurrentBlockState(self.StateComment)
            return
        self.setCurrentBlockState(self.StateNormal)
        self._highlight_markup(text, 0)

    def _highlight_markup(self, text: str, offset: int) -> None:
        start = self._comment_start.match(text)
        if start.hasMatch():
            before = text[: start.capturedStart()]
            self._apply_markup(before, offset)
            after = start.capturedStart()
            end = self._comment_end.match(text, after)
            if end.hasMatch():
                close_at = end.capturedStart() + end.capturedLength()
                self.setFormat(offset + after, close_at - after, _format(MUTED, italic=True))
                self._highlight_markup(text[close_at:], offset + close_at)
            else:
                self.setFormat(offset + after, len(text) - after, _format(MUTED, italic=True))
                self.setCurrentBlockState(self.StateComment)
            return
        self._apply_markup(text, offset)

    def _apply_markup(self, text: str, offset: int) -> None:
        self._apply(text, offset, self._tag, _format(COBALT, bold=True))
        self._apply(text, offset, self._attr, _format(_LITERAL))
        self._apply(text, offset, self._string, _format(_STRING))

    def _apply(
        self,
        text: str,
        offset: int,
        pattern: QRegularExpression,
        fmt: QTextCharFormat,
    ) -> None:
        match = pattern.globalMatch(text)
        while match.hasNext():
            captured = match.next()
            self.setFormat(
                offset + captured.capturedStart(),
                captured.capturedLength(),
                fmt,
            )


_C_KEYWORDS = (
    "auto",
    "break",
    "case",
    "char",
    "const",
    "continue",
    "default",
    "do",
    "double",
    "else",
    "enum",
    "extern",
    "float",
    "for",
    "goto",
    "if",
    "inline",
    "int",
    "long",
    "register",
    "restrict",
    "return",
    "short",
    "signed",
    "sizeof",
    "static",
    "struct",
    "switch",
    "typedef",
    "union",
    "unsigned",
    "void",
    "volatile",
    "while",
    "_Bool",
    "_Complex",
    "_Imaginary",
    "bool",
    "true",
    "false",
    "NULL",
)


class CHighlighter(QSyntaxHighlighter):
    StateNormal = 0
    StateComment = 1

    def __init__(self, parent: QTextDocument | None = None) -> None:
        super().__init__(parent)
        self._keyword = QRegularExpression(rf"\b(?:{'|'.join(_C_KEYWORDS)})\b")
        self._number = QRegularExpression(
            r"\b(?:0x[0-9A-Fa-f]+|\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\b"
        )
        self._string = QRegularExpression(r"(?:\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*')")
        self._preproc = QRegularExpression(r"^\s*#\s*[A-Za-z_]\w*")
        self._line_comment = QRegularExpression(r"//.*$")
        self._comment_start = QRegularExpression(r"/\*")
        self._comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        if self.previousBlockState() == self.StateComment:
            end = self._comment_end.match(text)
            if end.hasMatch():
                close_at = end.capturedStart() + end.capturedLength()
                self.setFormat(0, close_at, _format(MUTED, italic=True))
                self.setCurrentBlockState(self.StateNormal)
                self._highlight_code(text[close_at:], close_at)
            else:
                self.setFormat(0, len(text), _format(MUTED, italic=True))
                self.setCurrentBlockState(self.StateComment)
            return
        self.setCurrentBlockState(self.StateNormal)
        self._highlight_code(text, 0)

    def _highlight_code(self, text: str, offset: int) -> None:
        line = self._line_comment.match(text)
        block = self._comment_start.match(text)
        line_at = line.capturedStart() if line.hasMatch() else -1
        block_at = block.capturedStart() if block.hasMatch() else -1
        if line_at >= 0 and (block_at < 0 or line_at <= block_at):
            self._apply_code(text[:line_at], offset)
            self.setFormat(
                offset + line_at,
                len(text) - line_at,
                _format(MUTED, italic=True),
            )
            return
        if block_at >= 0:
            self._apply_code(text[:block_at], offset)
            end = self._comment_end.match(text, block_at + 2)
            if end.hasMatch():
                close_at = end.capturedStart() + end.capturedLength()
                self.setFormat(
                    offset + block_at,
                    close_at - block_at,
                    _format(MUTED, italic=True),
                )
                self._highlight_code(text[close_at:], offset + close_at)
            else:
                self.setFormat(
                    offset + block_at,
                    len(text) - block_at,
                    _format(MUTED, italic=True),
                )
                self.setCurrentBlockState(self.StateComment)
            return
        self._apply_code(text, offset)

    def _apply_code(self, text: str, offset: int) -> None:
        self._apply(text, offset, self._keyword, _format(COBALT, bold=True))
        self._apply(text, offset, self._number, _format(_NUMBER))
        self._apply(text, offset, self._preproc, _format(COBALT, bold=True))
        self._apply(text, offset, self._string, _format(_STRING))

    def _apply(
        self,
        text: str,
        offset: int,
        pattern: QRegularExpression,
        fmt: QTextCharFormat,
    ) -> None:
        match = pattern.globalMatch(text)
        while match.hasNext():
            captured = match.next()
            self.setFormat(
                offset + captured.capturedStart(),
                captured.capturedLength(),
                fmt,
            )


def highlighter_for(suffix: str, document: QTextDocument) -> QSyntaxHighlighter:
    language = suffix.lower()
    if language in {".yaml", ".yml"}:
        return YamlHighlighter(document)
    if language == ".xml":
        return XmlHighlighter(document)
    if language in {".c", ".h"}:
        return CHighlighter(document)
    return JsonHighlighter(document)
