<div align="center">
  <h1>Yet Another Bluetooth Low Energy (Debugger)</h1>
  <img src="https://github.com/H1M4W4R1/YABLE/blob/master/gh_images/screenshot.png" alt="Preview screenshot"/>
</div>


YABLE is a small desktop BLE debugging application for scanning nearby Bluetooth Low Energy devices, connecting to them, discovering GATT, and inspecting or changing characteristic values.

## Features

- Live BLE advertisement scanning.
- Device list with last advertisement age, RSSI value, and signal strength icon.
- Name keyword filter for the scan list: enter one or more comma-separated fragments and only devices whose advertised name contains any of them are listed (case-insensitive).
- Frameless window resizing by dragging any edge or corner, plus the bottom-right grip.
- Command tab for assembling JL protocol frames: edit HEAD, version, command and data; data can be JSON (encoded as UTF-8 before building) or binary hex such as `0x01`; length and CRC16 are calculated automatically.
- Copy the generated frame as space-separated hex for a characteristic write.
- Card-style device selector with advertised company names and GAP appearance when available.
- Connect and discover GATT services from the selected device.
- Foldout service groups with characteristics listed below each service.
- Friendly service, characteristic, and descriptor names from the Bluetooth Numbers Database.
- Read characteristic values when `read` is supported.
- Write characteristic values when `write` or `write-without-response` is supported.
- Read and write descriptor values from the GATT panel.
- Characteristic descriptors are collapsed under each characteristic by default.
- Enable and stop notifications or indications when available.
- Switch displayed value format from the characteristic context menu:
  - `HEX`
  - `DEC`
  - `OCT`
  - `BIN`
  - `ASCII`
  - `DATETIME`
- Use the same formats in the write dialog.
- Modern dark interface with cyan accents.

## Requirements

- Windows with Bluetooth LE support.
- Python 3.11 or newer.
- Python packages from `requirements.txt`.

## Installation

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Usage

```powershell
.\.venv\Scripts\python.exe main.py
```

Then:

1. Optionally type one or more name keywords into the Devices filter box, separated by commas (e.g. `Mi, Band`).
2. Click `Start scan`.
3. Select an advertised BLE device.
4. Click `Connect + GATT`.
5. Expand services and inspect characteristics.
6. Right-click a characteristic value to change its display format.

The filter is applied live: clearing it shows every device seen during the current session, and changing it re-checks the devices already in the list. Resize the window by dragging any edge or corner, or use the grip in the bottom-right corner.

## Command builder

The right side has `GATT` and `Command` tabs. The `Command` tab builds frames in this format:

| Byte | 0 | 1 | 2 | 3 | 4 | 5 | 6..n | n+1 | n+2 | n+3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Field | HEAD | HEAD | LEN | LEN | REV | CMD | DATA | CHK | CHK | END |

Only `HEAD`, `REV`, `CMD` and the data area are editable; everything else is generated:

- `HEAD`: two bytes, default `4A4C`. Command `0x02` may use a different header.
- `LEN`: big-endian `user_data_size` = version byte + command byte + data byte length.
- `REV`: protocol version byte, default `0x10`.
- `CMD`: command byte from the command set.
- `DATA`: select `JSON (UTF-8)` to enter JSON such as `{"ssid":"xxx","pass":"yyy"}`; the text is validated and encoded as UTF-8 before the frame is built. Select `Binary (hex)` to send raw bytes such as `0x01` or `0x01 0x02 FF` directly, with no JSON conversion.
- `CHK`: CRC16 (polynomial `0x1021`, initial value `0x0000`, no reflection) over `LEN` + `REV` + `CMD` + data bytes. `HEAD`, `CHK` and `END` are not covered.
- `END`: fixed `FF`.

The two CRC bytes default to high byte first; switch `CRC bytes` to `Low first` when the firmware expects the low byte first. `Copy HEX` copies the space-separated frame, which can be pasted into a characteristic write dialog using the `RAW` format. Leading and trailing whitespace in the JSON area is ignored, and the payload also builds when the JSON is not strictly valid so you can experiment. In `Binary (hex)` mode the spaces in `0x01 0x02 FF`, commas, `0x` prefixes and single-digit bytes are accepted.

When writing a frame to a characteristic, choose `RAW (exact bytes)` in the write dialog. The other formats parse the text as a value: `BIN` only accepts `0`/`1` digits (hex letters such as `4D` are rejected), and `HEX` converts a single number, which can reverse or truncate the bytes according to the endian setting and the characteristic's current length. The write dialog detects byte-like hex input and warns before sending, and offers to retry as `RAW` if a numeric format fails. Its `Remove spaces` option is enabled by default and strips spaces and line breaks from pasted hex commands before sending; plain text values keep their spaces.

## Notes

- BLE access depends on the operating system Bluetooth stack and adapter permissions.
- Some devices do not expose readable names or readable characteristic values.
- Writes and notifications are only shown when the characteristic properties advertise support for them.
- If characteristic CUD is set to "Service Name" (case and whitespace insensitive) then it will be displayed as service name

## License

This project is licensed under the [WTFPL](LICENSE.md).
