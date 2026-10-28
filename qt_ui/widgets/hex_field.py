from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLineEdit, QWidget

_HEX_SEPARATORS = (" ", "\t", ",", ":", "-", "_")


class HexField(QLineEdit):
    """Fixed-size hex byte input that accepts pasted '0x..' and spaced groups."""

    def __init__(self, byte_count: int, value: bytes, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.byte_count = byte_count
        self.setObjectName("HexField")
        self.setMaxLength(byte_count * 3 + 2)
        self.setFixedWidth(50 + byte_count * 14)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.setText(value.hex().upper())
        self.textChanged.connect(self._update_state)
        self.editingFinished.connect(self.normalize)

    def _compact(self, text: str) -> str:
        compact = text.strip()
        if compact.lower().startswith("0x"):
            compact = compact[2:]
        for separator in _HEX_SEPARATORS:
            compact = compact.replace(separator, "")
        return compact

    def value_bytes(self) -> bytes | None:
        compact = self._compact(self.text())
        if len(compact) != self.byte_count * 2:
            return None
        try:
            number = int(compact, 16)
        except ValueError:
            return None
        return number.to_bytes(self.byte_count, "big")

    def normalize(self) -> None:
        compact = self._compact(self.text())
        if not compact or len(compact) > self.byte_count * 2:
            return
        try:
            int(compact, 16)
        except ValueError:
            return
        normalized = compact.upper().zfill(self.byte_count * 2)
        if normalized != self.text():
            self.setText(normalized)

    def _update_state(self, text: str) -> None:
        invalid = bool(text.strip()) and self.value_bytes() is None
        if self.property("invalid") != invalid:
            self.setProperty("invalid", invalid)
            self.style().unpolish(self)
            self.style().polish(self)
