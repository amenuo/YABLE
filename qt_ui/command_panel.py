from __future__ import annotations

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QGuiApplication
from PyQt6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
)

from config import COLORS
from helpers.protocol import PROTOCOL_VERSION, ProtocolFrame, build_frame, json_error, parse_hex_payload
from qt_ui.icons import set_button_icon
from qt_ui.widgets.hex_field import HexField
# 这里修改默认的协议头
DEFAULT_HEAD = b"\x4D\x53"
DEFAULT_VERSION = bytes((PROTOCOL_VERSION,))
DEFAULT_COMMAND = b"\x01"
DEFAULT_JSON = '{"ssid":"xxx","pass":"yyy"}'


class CommandPanel(QFrame):
    """Builds protocol frames; HEAD, version, command and the data area are editable."""

    def __init__(self) -> None:
        super().__init__()
        self.setObjectName("TabPage")
        self.frame: ProtocolFrame | None = None
        self.build_ui()
        self.refresh_frame()

    def build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        title = QLabel("Amn frame")
        title.setObjectName("PanelTitle")
        subtitle = QLabel("Length and CRC16 are calculated automatically while you edit.")
        subtitle.setObjectName("Muted")
        subtitle.setWordWrap(True)
        title_stack = QVBoxLayout()
        title_stack.setSpacing(1)
        title_stack.addWidget(title)
        title_stack.addWidget(subtitle)

        self.copy_hint = QLabel("")
        self.copy_hint.setObjectName("Muted")
        self.copy_button = QPushButton("Copy HEX")
        self.copy_button.setObjectName("GhostButton")
        set_button_icon(self.copy_button, "fa5s.copy", COLORS["text"])
        self.copy_button.setEnabled(False)
        self.copy_button.setToolTip("Copy the space-separated frame bytes (use with the RAW write format).")
        self.copy_button.clicked.connect(self.copy_hex)

        header = QHBoxLayout()
        header.addLayout(title_stack, 1)
        header.addWidget(self.copy_hint)
        header.addWidget(self.copy_button)

        fields = QGridLayout()
        fields.setHorizontalSpacing(10)
        fields.setVerticalSpacing(4)
        head_caption = self.make_caption(
            "HEAD (2 bytes)",
            "Protocol header, for example 4A4C. Command 0x02 may use a different header.",
        )
        version_caption = self.make_caption("Version", "Protocol version byte, default 0x10.")
        command_caption = self.make_caption("Command", "Command byte from the command set.")
        crc_caption = self.make_caption("CRC bytes", "Byte order of the two CRC16 bytes in the frame.")
        fields.addWidget(head_caption, 0, 0)
        fields.addWidget(version_caption, 0, 1)
        fields.addWidget(command_caption, 0, 2)
        fields.addWidget(crc_caption, 0, 3)

        self.head_field = HexField(2, DEFAULT_HEAD)
        self.version_field = HexField(1, DEFAULT_VERSION)
        self.command_field = HexField(1, DEFAULT_COMMAND)
        self.crc_order_box = QComboBox()
        self.crc_order_box.addItem("High first", "big")
        self.crc_order_box.addItem("Low first", "little")
        self.crc_order_box.setToolTip("Byte order of the two CRC16 bytes in the frame.")
        fields.addWidget(self.head_field, 1, 0)
        fields.addWidget(self.version_field, 1, 1)
        fields.addWidget(self.command_field, 1, 2)
        fields.addWidget(self.crc_order_box, 1, 3)
        fields.setColumnStretch(4, 1)

        length_block, self.length_value = self.make_stat(
            "LENGTH",
            "user_data_size = version byte + command byte + data bytes.",
        )
        crc_block, self.crc_value = self.make_stat(
            "CRC16",
            "CRC16 over LEN, REV, CMD and data bytes. Does not cover HEAD, CRC itself or END.",
        )
        size_block, self.size_value = self.make_stat(
            "FRAME",
            "Total frame size including HEAD, LEN, CRC and END.",
        )
        stats = QHBoxLayout()
        stats.setSpacing(8)
        stats.addWidget(length_block, 1)
        stats.addWidget(crc_block, 1)
        stats.addWidget(size_block, 1)

        data_title = QLabel("Data")
        data_title.setObjectName("SmallTitle")
        self.data_mode_box = QComboBox()
        self.data_mode_box.setObjectName("DataMode")
        self.data_mode_box.addItem("JSON (UTF-8)", "json")
        self.data_mode_box.addItem("Binary (hex)", "binary")
        self.data_mode_box.setToolTip(
            "JSON: the text is validated and encoded as UTF-8 before the frame is built.\n"
            "Binary: enter raw bytes as hex, for example 0x01 or 0x01 0x02 FF."
        )
        self.data_status = QLabel("")
        self.data_status.setObjectName("DataStatus")
        self.data_status.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        data_header = QHBoxLayout()
        data_header.addWidget(data_title)
        data_header.addWidget(self.data_mode_box)
        data_header.addStretch(1)
        data_header.addWidget(self.data_status)

        self.json_editor = QPlainTextEdit()
        self.json_editor.setObjectName("JsonEditor")
        self.json_editor.setPlaceholderText(DEFAULT_JSON)
        self.json_editor.setPlainText(DEFAULT_JSON)
        self.json_editor.setTabChangesFocus(True)
        self.json_editor.setMinimumHeight(110)
        self.json_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        self.binary_editor = QPlainTextEdit()
        self.binary_editor.setObjectName("BinaryEditor")
        self.binary_editor.setPlaceholderText("0x01 0x02 FF")
        self.binary_editor.setTabChangesFocus(True)
        self.binary_editor.setMinimumHeight(110)
        self.binary_editor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)

        self.data_stack = QStackedWidget()
        self.data_stack.setObjectName("DataStack")
        self.data_stack.addWidget(self.json_editor)
        self.data_stack.addWidget(self.binary_editor)

        preview_title = QLabel("Frame preview")
        preview_title.setObjectName("SmallTitle")
        preview_header = QHBoxLayout()
        preview_header.addWidget(preview_title)
        preview_header.addStretch(1)
        preview_header.addWidget(self.make_hint("space-separated hex"))

        self.preview = QLabel("—")
        self.preview.setObjectName("FramePreview")
        self.preview.setWordWrap(True)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        self.field_map = QLabel("")
        self.field_map.setObjectName("FieldMap")
        self.field_map.setWordWrap(True)
        self.field_map.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        layout.addLayout(header)
        layout.addLayout(fields)
        layout.addLayout(stats)
        layout.addSpacing(2)
        layout.addLayout(data_header)
        layout.addWidget(self.data_stack, 1)
        layout.addLayout(preview_header)
        layout.addWidget(self.preview)
        layout.addWidget(self.field_map)

        for field in (self.head_field, self.version_field, self.command_field):
            field.textChanged.connect(self.refresh_frame)
        self.crc_order_box.currentIndexChanged.connect(self.refresh_frame)
        self.data_mode_box.currentIndexChanged.connect(self.on_data_mode_changed)
        self.json_editor.textChanged.connect(self.refresh_frame)
        self.binary_editor.textChanged.connect(self.refresh_frame)

        self.copy_timer = QTimer(self)
        self.copy_timer.setSingleShot(True)
        self.copy_timer.timeout.connect(lambda: self.copy_hint.setText(""))

    @staticmethod
    def make_caption(text: str, tooltip: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("Muted")
        label.setToolTip(tooltip)
        return label

    @staticmethod
    def make_hint(text: str) -> QLabel:
        label = QLabel(text)
        label.setObjectName("MonoMuted")
        return label

    @staticmethod
    def make_stat(caption: str, tooltip: str) -> tuple[QFrame, QLabel]:
        block = QFrame()
        block.setObjectName("StatBlock")
        block.setToolTip(tooltip)
        block_layout = QVBoxLayout(block)
        block_layout.setContentsMargins(10, 7, 10, 7)
        block_layout.setSpacing(1)
        caption_label = QLabel(caption)
        caption_label.setObjectName("StatCaption")
        value_label = QLabel("—")
        value_label.setObjectName("StatValue")
        value_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        block_layout.addWidget(caption_label)
        block_layout.addWidget(value_label)
        return block, value_label

    def on_data_mode_changed(self) -> None:
        self.data_stack.setCurrentIndex(1 if self.data_mode_box.currentData() == "binary" else 0)
        self.refresh_frame()

    def refresh_frame(self) -> None:
        head = self.head_field.value_bytes()
        version = self.version_field.value_bytes()
        command = self.command_field.value_bytes()
        if self.data_mode_box.currentData() == "binary":
            try:
                payload = parse_hex_payload(self.binary_editor.toPlainText())
            except ValueError as exc:
                self.update_binary_status(str(exc), 0)
                self.set_frame(None, str(exc))
                return
            self.update_binary_status(None, len(payload))
        else:
            payload_text = self.json_editor.toPlainText().strip()
            payload = payload_text.encode("utf-8")
            self.update_json_status(payload_text, len(payload))

        if head is None or version is None or command is None:
            self.set_frame(None, "Enter a complete HEAD, version and command to build the frame.")
            return

        try:
            frame = build_frame(
                head,
                version[0],
                command[0],
                payload,
                crc_low_first=self.crc_order_box.currentData() == "little",
            )
        except ValueError as exc:
            self.set_frame(None, str(exc))
            return

        self.set_frame(frame, "")

    def set_frame(self, frame: ProtocolFrame | None, message: str) -> None:
        self.frame = frame
        self.copy_button.setEnabled(frame is not None)
        if frame is None:
            self.length_value.setText("—")
            self.crc_value.setText("—")
            self.size_value.setText("—")
            self.preview.setText(message or "—")
            self.field_map.setText("")
            return
        self.length_value.setText(f"0x{frame.user_data_size:04X}  ({frame.user_data_size} B)")
        self.crc_value.setText(f"0x{frame.crc:04X}")
        self.size_value.setText(f"{len(frame.raw)} B")
        self.preview.setText(frame.hex_text)
        self.field_map.setText(frame.field_summary)

    def set_data_status(self, state: str, text: str, tooltip: str = "") -> None:
        self.data_status.setText(text)
        self.data_status.setToolTip(tooltip)
        if self.data_status.property("state") != state:
            self.data_status.setProperty("state", state)
            self.data_status.style().unpolish(self.data_status)
            self.data_status.style().polish(self.data_status)

    def update_json_status(self, payload_text: str, byte_count: int) -> None:
        if not payload_text:
            self.set_data_status("muted", "Empty payload · 0 B")
            return
        error = json_error(payload_text)
        if error is None:
            self.set_data_status("ok", f"Valid JSON · {byte_count} B (UTF-8)")
        else:
            self.set_data_status("bad", f"Invalid JSON · {error}", error)

    def update_binary_status(self, error: str | None, byte_count: int) -> None:
        if error is not None:
            self.set_data_status("bad", error, error)
        elif byte_count == 0:
            self.set_data_status("muted", "Empty payload · 0 B")
        else:
            self.set_data_status("ok", f"Valid hex · {byte_count} B")

    def copy_hex(self) -> None:
        if self.frame is None:
            return
        QGuiApplication.clipboard().setText(self.frame.hex_text)
        self.copy_hint.setText("Copied")
        self.copy_timer.start(1500)
