from __future__ import annotations

from collections.abc import Callable

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox, QDialog, QHBoxLayout, QLabel, QMessageBox, QPushButton, QTextEdit, QVBoxLayout, QWidget

from config import COLORS
from helpers.formatting import ValueFormat, bytes_to_text, text_to_bytes
from models import CharacteristicModel, DescriptorModel
from qt_ui.icons import set_button_icon

FORMAT_SUMMARY = {
    ValueFormat.HEX: "number",
    ValueFormat.DEC: "number",
    ValueFormat.OCT: "number",
    ValueFormat.BIN: "number",
    ValueFormat.ASCII: "text",
    ValueFormat.DATETIME: "timestamp",
    ValueFormat.RAW: "exact bytes",
}

FORMAT_HINT = {
    ValueFormat.HEX: (
        "Parses one hex number and re-encodes it with the characteristic's endian setting and current length. "
        "Use RAW to send a frame byte-for-byte."
    ),
    ValueFormat.DEC: "Parses one decimal number and re-encodes it with the characteristic's endian setting.",
    ValueFormat.OCT: "Parses one octal number and re-encodes it with the characteristic's endian setting.",
    ValueFormat.BIN: "Parses one binary number from 0/1 digits only; hex letters such as 4D are rejected. Use RAW for frames.",
    ValueFormat.ASCII: "Sends the text as UTF-8 bytes.",
    ValueFormat.DATETIME: "Parses a Unix timestamp and writes it as 4 or 8 bytes.",
    ValueFormat.RAW: "Sends the hex bytes exactly as entered. Spaces, commas and 0x prefixes are ignored.",
}


class WriteDialog(QDialog):
    remove_spaces_default = True

    def __init__(
        self,
        parent: QWidget,
        target: CharacteristicModel | DescriptorModel,
        on_write: Callable[[bytes], None],
    ) -> None:
        super().__init__(parent)
        self.target = target
        self.on_write = on_write
        self.setWindowTitle(f"Write {target.name}")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(10)

        title = QLabel(target.name)
        title.setObjectName("DialogTitle")
        uuid = QLabel(target.uuid)
        uuid.setObjectName("Muted")

        self.format_box = QComboBox()
        for fmt in ValueFormat:
            self.format_box.addItem(f"{fmt.value} ({FORMAT_SUMMARY[fmt]})", fmt.value)
            self.format_box.setItemData(self.format_box.count() - 1, FORMAT_HINT[fmt], Qt.ItemDataRole.ToolTipRole)
        index = self.format_box.findData(target.display_format.value)
        self.format_box.setCurrentIndex(max(0, index))

        self.format_hint = QLabel("")
        self.format_hint.setObjectName("FormatHint")
        self.format_hint.setWordWrap(True)

        self.remove_spaces_check = QCheckBox("Remove spaces")
        self.remove_spaces_check.setChecked(WriteDialog.remove_spaces_default)
        self.remove_spaces_check.setToolTip(
            "Remove spaces, tabs and line breaks from hex command input before sending.\n"
            "Plain text values keep their spaces."
        )
        self.remove_spaces_check.toggled.connect(self.remember_remove_spaces)
        self.remove_spaces_check.toggled.connect(self.refresh_format_hint)

        self.editor = QTextEdit()
        self.editor.setObjectName("ValueEditor")
        self.editor.setMinimumHeight(120)
        self.editor.setPlainText(bytes_to_text(target.value, target.display_format, target.display_endian))
        self.editor.textChanged.connect(self.refresh_format_hint)
        self.format_box.currentIndexChanged.connect(self.refresh_format_hint)

        row = QHBoxLayout()
        row.addWidget(QLabel("Format"))
        row.addWidget(self.format_box, 1)
        row.addWidget(self.remove_spaces_check)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel_button = QPushButton("Cancel")
        cancel_button.setObjectName("GhostButton")
        set_button_icon(cancel_button, "fa5s.times", COLORS["text"])
        cancel_button.clicked.connect(self.reject)
        write_button = QPushButton("Write")
        write_button.setObjectName("AccentButton")
        set_button_icon(write_button, "fa5s.pen", "#061018")
        write_button.clicked.connect(self._write)
        buttons.addWidget(cancel_button)
        buttons.addWidget(write_button)

        layout.addWidget(title)
        layout.addWidget(uuid)
        layout.addLayout(row)
        layout.addWidget(self.format_hint)
        layout.addWidget(QLabel("Value"))
        layout.addWidget(self.editor)
        layout.addLayout(buttons)

        self.refresh_format_hint()

    def selected_format(self) -> ValueFormat:
        return ValueFormat(str(self.format_box.currentData()))

    @staticmethod
    def looks_like_hex_bytes(text: str) -> bytes | None:
        stripped = text.strip()
        if not stripped:
            return None
        has_separator = any(character.isspace() or character in ",:-_" for character in stripped)
        compact = "".join(character for character in stripped if not character.isspace())
        compact = compact.replace("0x", "").replace("0X", "")
        for separator in (",", ":", "-", "_"):
            compact = compact.replace(separator, "")
        if len(compact) < 4 or len(compact) % 2:
            return None
        try:
            data = bytes.fromhex(compact)
        except ValueError:
            return None
        if len(data) >= 8 or has_separator:
            return data
        return None

    def refresh_format_hint(self) -> None:
        fmt = self.selected_format()
        raw = self.looks_like_hex_bytes(self.editor.toPlainText())
        if raw is not None and fmt != ValueFormat.RAW:
            text = f"Looks like a raw hex byte sequence ({len(raw)} bytes). Select RAW to send it unchanged."
            state = "warning"
        else:
            text = FORMAT_HINT[fmt]
            state = "normal"
        if raw is not None and self.remove_spaces_check.isChecked() and fmt != ValueFormat.RAW:
            text += " Spaces and line breaks are removed before sending."
        self.format_hint.setText(text)
        if self.format_hint.property("state") != state:
            self.format_hint.setProperty("state", state)
            self.format_hint.style().unpolish(self.format_hint)
            self.format_hint.style().polish(self.format_hint)

    def input_text(self) -> str:
        text = self.editor.toPlainText().strip()
        if self.remove_spaces_check.isChecked() and self.looks_like_hex_bytes(text) is not None:
            return "".join(text.split())
        return text

    @staticmethod
    def remember_remove_spaces(checked: bool) -> None:
        WriteDialog.remove_spaces_default = checked

    def _write(self) -> None:
        fmt = self.selected_format()
        text = self.input_text()
        try:
            byte_length = len(self.target.value) if self.target.value else None
            data = text_to_bytes(text, fmt, self.target.display_endian, byte_length)
        except Exception as exc:
            raw = self.looks_like_hex_bytes(text)
            if raw is not None and fmt != ValueFormat.RAW:
                answer = QMessageBox.question(
                    self,
                    "Send as RAW?",
                    f"This looks like a raw hex byte sequence ({len(raw)} bytes), but {fmt.value} treats the text as a number.\n\n"
                    "Send it unchanged as RAW instead?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if answer == QMessageBox.StandardButton.Yes:
                    self.on_write(raw)
                    self.accept()
                    return
            QMessageBox.critical(self, "Invalid value", str(exc))
            return
        self.on_write(data)
        self.accept()
