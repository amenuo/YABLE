from __future__ import annotations

import json
from dataclasses import dataclass

PROTOCOL_VERSION = 0x10
END_MARKER = 0xFF

_HEX_DIGITS = frozenset("0123456789abcdefABCDEF")

_CRC16_TABLE = (
    0x0000,
    0x1021,
    0x2042,
    0x3063,
    0x4084,
    0x50A5,
    0x60C6,
    0x70E7,
    0x8108,
    0x9129,
    0xA14A,
    0xB16B,
    0xC18C,
    0xD1AD,
    0xE1CE,
    0xF1EF,
)


def crc16(data: bytes | bytearray | memoryview) -> int:
    """CRC16-CCITT as used by the device firmware (init 0, poly 0x1021, no reflection)."""
    crc = 0
    for byte in data:
        crc = ((crc << 4) & 0xFFFF) ^ _CRC16_TABLE[(crc >> 12) ^ (byte >> 4)]
        crc = ((crc << 4) & 0xFFFF) ^ _CRC16_TABLE[(crc >> 12) ^ (byte & 0x0F)]
    return crc


def json_error(text: str) -> str | None:
    """Return a readable JSON error, or None when the text is valid JSON."""
    try:
        json.loads(text)
    except json.JSONDecodeError as exc:
        return f"{exc.msg} (line {exc.lineno}, column {exc.colno})"
    return None


def parse_hex_payload(text: str) -> bytes:
    """Parse raw data entered as hex bytes, e.g. '0x01' or '0x01 02 FF'."""
    compact = ""
    normalized = text.replace(",", " ").replace(";", " ").replace("\n", " ")
    for token in normalized.split():
        token = token.replace("_", "").replace("-", "").replace(":", "")
        if token.lower().startswith("0x"):
            token = token[2:]
        if not token:
            continue
        if any(character not in _HEX_DIGITS for character in token):
            raise ValueError(f"Invalid hex data: {token!r}")
        if len(token) % 2:
            token = "0" + token
        compact += token
    return bytes.fromhex(compact)


@dataclass(frozen=True)
class ProtocolFrame:
    head: bytes
    version: int
    command: int
    payload: bytes
    user_data_size: int
    crc: int
    crc_bytes: bytes
    raw: bytes

    @property
    def hex_text(self) -> str:
        return " ".join(f"{byte:02X}" for byte in self.raw)

    @property
    def field_summary(self) -> str:
        return (
            f"HEAD {self.head.hex(' ').upper()}  ·  LEN {self.user_data_size:04X}  ·  "
            f"REV {self.version:02X}  ·  CMD {self.command:02X}  ·  "
            f"CRC {self.crc_bytes.hex(' ').upper()}  ·  END {END_MARKER:02X}"
        )


def build_frame(
    head: bytes,
    version: int,
    command: int,
    payload: bytes,
    crc_low_first: bool = False,
) -> ProtocolFrame:
    """Assemble HEAD + LEN + REV + CMD + JSON + CRC16 + END.

    LEN (user_data_size) = version byte + command byte + payload bytes.
    CRC16 covers LEN, REV, CMD and payload.
    """
    if len(head) != 2:
        raise ValueError("HEAD must be exactly 2 bytes")
    if not 0 <= version <= 0xFF:
        raise ValueError("Version must fit in one byte")
    if not 0 <= command <= 0xFF:
        raise ValueError("Command must fit in one byte")

    payload = bytes(payload)
    user_data_size = 2 + len(payload)
    if user_data_size > 0xFFFF:
        raise ValueError("Payload is too large for the 16-bit length field")

    body = user_data_size.to_bytes(2, "big") + bytes((version, command)) + payload
    crc = crc16(body)
    crc_bytes = crc.to_bytes(2, "little" if crc_low_first else "big")
    raw = head + body + crc_bytes + bytes((END_MARKER,))
    return ProtocolFrame(
        head=head,
        version=version,
        command=command,
        payload=payload,
        user_data_size=user_data_size,
        crc=crc,
        crc_bytes=crc_bytes,
        raw=raw,
    )
