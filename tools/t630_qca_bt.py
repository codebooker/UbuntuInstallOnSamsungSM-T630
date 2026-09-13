#!/usr/bin/env python3
"""Bring up the SM-T630 WCN6850 Bluetooth controller over /dev/ttyHS0.

The controller boots without its RAM patch.  This helper follows Qualcomm's
published Bluetooth HAL protocol: query the ROM, switch the UART to 3.2 Mbit,
download Samsung's hpbtfw10/hpnv10 TLVs, then attach the Linux Qualcomm H4
line discipline.  That transport understands the controller's 0xfd/0xfc/0xfe in-band sleep
handshake used by this controller.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import os
import re
import select
import signal
import struct
import sys
import termios
import time
import xml.etree.ElementTree as ET
from pathlib import Path


HCI_COMMAND_PKT = 0x01
HCI_EVENT_PKT = 0x04
HCI_IBS_WAKE_ACK = 0xFC
HCI_IBS_WAKE_IND = 0xFD
HCI_IBS_SLEEP_IND = 0xFE
EVT_CMD_COMPLETE = 0x0E
EVT_VENDOR = 0xFF
EDL_PATCH_OPCODE = 0xFC00
EDL_SET_BAUD_OPCODE = 0xFC48
EDL_PATCH_VER_REQ = 0x19
EDL_TLV_DOWNLOAD_REQ = 0x1E
EDL_GET_BOARD_ID = 0x23
MAX_TLV_SEGMENT = 243
BAUD_CODE_3200000 = 0x11

N_TTY = 0
N_HCI = 15
HCI_UART_QCA = 8
HCI_UART_H4 = 0
TIOCSETD = 0x5423
TIOCMGET = 0x5415
TIOCMSET = 0x5418
TIOCM_RTS = 0x004
HCIUARTSETPROTO = 0x400455C8
HCIUARTSETFLAGS = 0x400455CB
TCGETS2 = 0x802C542A
TCSETSW2 = 0x402C542B
CBAUD = 0x100F
BOTHER = 0x1000


def log(message: str) -> None:
    print(f"t630-bluetooth: {message}", flush=True)


def parse_bdaddr(value: str) -> bytes:
    value = value.strip()
    if not re.fullmatch(r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}", value):
        raise ValueError(f"invalid Bluetooth address: {value!r}")
    return bytes.fromhex(value.replace(":", ""))


def format_bdaddr(value: bytes) -> str:
    return ":".join(f"{byte:02x}" for byte in value)


def iter_nvm_tags(blob: bytes | bytearray):
    if len(blob) < 4 or blob[0] != 2:
        raise ValueError("not a Qualcomm Bluetooth NVM TLV")
    declared = int.from_bytes(blob[1:4], "little")
    if declared + 4 > len(blob):
        raise ValueError("truncated Qualcomm NVM TLV")
    offset = 4
    end = 4 + declared
    while offset < end:
        if offset + 12 > end:
            raise ValueError("truncated NVM tag header")
        tag_id, tag_len = struct.unpack_from("<HH", blob, offset)
        data_offset = offset + 12
        next_offset = data_offset + tag_len
        if next_offset > end:
            raise ValueError(f"truncated NVM tag {tag_id}")
        yield tag_id, data_offset, tag_len
        offset = next_offset
    if offset != end:
        raise ValueError("invalid Qualcomm NVM TLV length")


def _xml_values(node: ET.Element) -> list[int]:
    children = list(node)
    if children:
        def index(item: ET.Element) -> int:
            match = re.search(r"(\d+)$", item.tag)
            return int(match.group(1)) if match else 0

        return [int(item.attrib["value"], 0) for item in sorted(children, key=index)]
    return [int(token, 0) for token in re.findall(r"0x[0-9a-fA-F]+|\d+", node.text or "")]


def apply_xml_overrides(blob: bytearray, xml_path: Path) -> set[int]:
    tags = {tag_id: (start, length) for tag_id, start, length in iter_nvm_tags(blob)}
    changed: set[int] = set()
    root = ET.parse(xml_path).getroot()
    for node in root:
        match = re.fullmatch(r"Tag(\d+)", node.tag)
        if not match:
            continue
        tag_id = int(match.group(1))
        if tag_id not in tags:
            raise ValueError(f"XML override references absent NVM tag {tag_id}")
        start, actual_len = tags[tag_id]
        expected_len = int(node.find("Length").attrib["len"], 0)
        if expected_len != actual_len:
            raise ValueError(
                f"NVM tag {tag_id} length is {actual_len}, XML expects {expected_len}"
            )
        values = _xml_values(node.find("Changes"))
        change_type = node.find("ChangeType").attrib["type"]
        if change_type == "entire":
            if len(values) != actual_len:
                raise ValueError(
                    f"XML supplies {len(values)} bytes for {actual_len}-byte tag {tag_id}"
                )
            blob[start : start + actual_len] = bytes(values)
        elif change_type == "default":
            offsets = _xml_values(node.find("Offset"))
            if len(offsets) != len(values):
                raise ValueError(f"XML offset/value mismatch for tag {tag_id}")
            for offset, value in zip(offsets, values):
                if offset >= actual_len:
                    raise ValueError(f"XML offset {offset} exceeds tag {tag_id}")
                blob[start + offset] = value
        else:
            raise ValueError(f"unknown XML change type {change_type!r}")
        changed.add(tag_id)
    return changed


def patch_nvm(
    source: bytes,
    xml_path: Path | None,
    bdaddr: bytes,
    baud_code: int = BAUD_CODE_3200000,
    enable_ibs: bool = True,
) -> tuple[bytes, set[int]]:
    blob = bytearray(source)
    changed = apply_xml_overrides(blob, xml_path) if xml_path else set()
    tags = {tag_id: (start, length) for tag_id, start, length in iter_nvm_tags(blob)}

    start, length = tags[2]
    if length != 6:
        raise ValueError("Bluetooth address tag has an unexpected length")
    blob[start : start + 6] = bdaddr[::-1]
    changed.add(2)

    start, length = tags[17]
    if length < 2:
        raise ValueError("UART settings tag is too short")
    if enable_ibs:
        blob[start] |= 0x80
    else:
        blob[start] &= ~0x80
    blob[start + 1] = baud_code
    changed.add(17)

    start, length = tags[27]
    if length < 1:
        raise ValueError("sleep settings tag is too short")
    if enable_ibs:
        blob[start] |= 0x01
    else:
        blob[start] &= ~0x01
    changed.add(27)
    return bytes(blob), changed


def firmware_info(blob: bytes) -> dict[str, int]:
    if len(blob) < 24 or blob[0] not in (1, 5):
        raise ValueError("not a Qualcomm RAM-patch TLV")
    return {
        "type": blob[0],
        "length": int.from_bytes(blob[1:4], "little"),
        "download_mode": blob[14],
        "product_id": int.from_bytes(blob[16:18], "little"),
        "rom_build": int.from_bytes(blob[18:20], "little"),
        "patch_version": int.from_bytes(blob[20:22], "little"),
    }


def _read_exact(fd: int, length: int, timeout: float = 2.0) -> bytes:
    result = bytearray()
    deadline = time.monotonic() + timeout
    while len(result) < length:
        remaining = deadline - time.monotonic()
        if remaining <= 0 or not select.select([fd], [], [], remaining)[0]:
            raise TimeoutError(f"UART timed out after {len(result)}/{length} bytes")
        chunk = os.read(fd, length - len(result))
        if not chunk:
            raise OSError("UART returned end-of-file")
        result.extend(chunk)
    return bytes(result)


def read_event(fd: int, timeout: float = 2.0, *, allow_ibs_ack: bool = False) -> bytes:
    deadline = time.monotonic() + timeout
    while True:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("no HCI event from controller")
        packet_type = _read_exact(fd, 1, remaining)[0]
        if packet_type == HCI_EVENT_PKT:
            header = _read_exact(fd, 2, remaining)
            return bytes([packet_type]) + header + _read_exact(fd, header[1], remaining)
        if packet_type in (HCI_IBS_WAKE_ACK, HCI_IBS_SLEEP_IND) and allow_ibs_ack:
            return bytes([packet_type])
        if packet_type == HCI_IBS_WAKE_IND:
            os.write(fd, bytes([HCI_IBS_WAKE_ACK]))
            continue
        log(f"ignoring UART byte 0x{packet_type:02x} while waiting for an event")


def wake_controller(fd: int, timeout: float = 1.0) -> None:
    """Wake an IBS-capable controller before sending a setup command."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        _write_all(fd, bytes([HCI_IBS_WAKE_IND]))
        attempt_deadline = min(deadline, time.monotonic() + 0.1)
        while time.monotonic() < attempt_deadline:
            remaining = attempt_deadline - time.monotonic()
            if not select.select([fd], [], [], remaining)[0]:
                break
            value = os.read(fd, 1)
            if not value:
                raise OSError("UART returned end-of-file")
            if value[0] == HCI_IBS_WAKE_ACK:
                return
            if value[0] == HCI_IBS_WAKE_IND:
                _write_all(fd, bytes([HCI_IBS_WAKE_ACK]))
            elif value[0] != HCI_IBS_SLEEP_IND:
                log(f"ignoring UART byte 0x{value[0]:02x} while waking controller")
    raise TimeoutError("controller did not acknowledge IBS wake")


def hci_command(opcode: int, params: bytes = b"") -> bytes:
    return bytes([HCI_COMMAND_PKT]) + struct.pack("<HB", opcode, len(params)) + params


def _write_all(fd: int, data: bytes) -> None:
    offset = 0
    while offset < len(data):
        written = os.write(fd, data[offset:])
        if written <= 0:
            raise OSError("short write to Bluetooth UART")
        offset += written


def event_opcode(event: bytes) -> int | None:
    if len(event) >= 6 and event[1] == EVT_CMD_COMPLETE:
        return int.from_bytes(event[4:6], "little")
    return None


def is_unified_version_event(event: bytes) -> bool:
    return (
        len(event) > 7
        and event[1] == EVT_CMD_COMPLETE
        and event_opcode(event) == EDL_PATCH_OPCODE
        and event[7] == EDL_PATCH_VER_REQ
    )


def parse_version_event(event: bytes, unified: bool) -> dict[str, int]:
    offsets = (9, 13, 15, 17) if unified else (5, 9, 11, 13)
    product, patch, rom, soc = offsets
    if len(event) < soc + 4:
        raise ValueError(f"short controller version event: {event.hex()}")
    return {
        "product_id": int.from_bytes(event[product : product + 4], "little"),
        "patch_version": int.from_bytes(event[patch : patch + 2], "little"),
        "rom_build": int.from_bytes(event[rom : rom + 2], "little"),
        "soc_id": int.from_bytes(event[soc : soc + 4], "little"),
    }


def parse_board_id(event: bytes, unified: bool) -> str | None:
    if unified:
        if len(event) < 11 or event[7] != EDL_GET_BOARD_ID:
            return None
        length, msb, lsb = event[8:11]
    else:
        if len(event) < 8 or event[4] != EDL_GET_BOARD_ID:
            return None
        length, msb, lsb = event[5:8]
    if length != 2:
        return None
    return f"{((msb << 8) | lsb):02x}"


def set_rts(fd: int, enabled: bool) -> None:
    state = bytearray(struct.pack("i", 0))
    fcntl.ioctl(fd, TIOCMGET, state, True)
    value = struct.unpack("i", state)[0]
    value = value | TIOCM_RTS if enabled else value & ~TIOCM_RTS
    fcntl.ioctl(fd, TIOCMSET, struct.pack("i", value))


def set_custom_baud(fd: int, speed: int) -> None:
    raw = bytearray(44)
    fcntl.ioctl(fd, TCGETS2, raw, True)
    fields = list(struct.unpack("=IIIIB19BII", raw))
    fields[2] = (fields[2] & ~CBAUD) | BOTHER
    fields[-2] = speed
    fields[-1] = speed
    fcntl.ioctl(fd, TCSETSW2, struct.pack("=IIIIB19BII", *fields))
    verified = bytearray(44)
    fcntl.ioctl(fd, TCGETS2, verified, True)
    current = struct.unpack("=IIIIB19BII", verified)
    if current[-2:] != (speed, speed):
        raise OSError(f"UART baud verification failed: {current[-2:]}")


def configure_uart(fd: int) -> None:
    attrs = termios.tcgetattr(fd)
    attrs[0] = 0
    attrs[1] = 0
    attrs[2] = termios.CS8 | termios.CREAD | termios.CLOCAL | termios.CRTSCTS
    attrs[3] = 0
    attrs[4] = termios.B115200
    attrs[5] = termios.B115200
    attrs[6][termios.VMIN] = 1
    attrs[6][termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW, attrs)
    termios.tcflush(fd, termios.TCIOFLUSH)


class Controller:
    def __init__(self, fd: int):
        self.fd = fd
        self.unified = False

    def query_version(self) -> dict[str, int]:
        _write_all(self.fd, hci_command(EDL_PATCH_OPCODE, bytes([EDL_PATCH_VER_REQ])))
        first = read_event(self.fd)
        self.unified = is_unified_version_event(first)
        version_event = first
        if not self.unified:
            if first[1] != EVT_VENDOR:
                raise ValueError(f"unexpected version response: {first.hex()}")
            read_event(self.fd)  # Legacy controllers send a following command-complete.
        return parse_version_event(version_event, self.unified)

    def set_high_speed(self) -> None:
        set_rts(self.fd, False)
        _write_all(self.fd, hci_command(EDL_SET_BAUD_OPCODE, bytes([BAUD_CODE_3200000])))
        time.sleep(0.020)
        termios.tcdrain(self.fd)
        set_custom_baud(self.fd, 3_200_000)
        set_rts(self.fd, True)
        response = read_event(self.fd, allow_ibs_ack=True)
        if response == b"\xfc":
            # WCN6850 may answer the post-flow-control transition with its
            # in-band wake acknowledgement instead of a second HCI event.
            log("controller acknowledged the high-speed UART transition")
        elif response == bytes([HCI_IBS_SLEEP_IND]):
            # WCN6850 may instead emit only its receive-side idle notice.
            # Its command receiver remains available for the TLV download.
            log("controller completed the high-speed UART transition")
        elif not self.unified:
            read_event(self.fd)

    def download_tlv(self, blob: bytes, *, patch: bool) -> None:
        mode = firmware_info(blob)["download_mode"] if patch else 0
        total = (len(blob) + MAX_TLV_SEGMENT - 1) // MAX_TLV_SEGMENT
        for index, offset in enumerate(range(0, len(blob), MAX_TLV_SEGMENT)):
            segment = blob[offset : offset + MAX_TLV_SEGMENT]
            last = index == total - 1
            params = bytes([EDL_TLV_DOWNLOAD_REQ, len(segment)]) + segment
            _write_all(self.fd, hci_command(EDL_PATCH_OPCODE, params))
            if patch and mode == 3 and not last:
                continue
            read_event(self.fd)
            if not self.unified and not patch:
                read_event(self.fd)
            if index == 0 or last or (index + 1) % 100 == 0:
                log(f"downloaded TLV segment {index + 1}/{total}")

    def query_board_id(self) -> str | None:
        _write_all(self.fd, hci_command(EDL_PATCH_OPCODE, bytes([EDL_GET_BOARD_ID])))
        first = read_event(self.fd)
        board_id = parse_board_id(first, self.unified)
        if not self.unified:
            read_event(self.fd)
        return board_id

    def reset(self) -> None:
        _write_all(self.fd, hci_command(0x0C03))
        event = read_event(self.fd)
        if event_opcode(event) != 0x0C03 or len(event) < 7 or event[6] != 0:
            raise ValueError(f"unexpected HCI reset response: {event.hex()}")


def persistent_address(path: Path) -> bytes:
    if path.exists():
        return parse_bdaddr(path.read_text().strip())
    seed = Path("/etc/machine-id").read_bytes() if Path("/etc/machine-id").exists() else os.urandom(32)
    address = bytearray(hashlib.sha256(b"SM-T630 Bluetooth\0" + seed).digest()[:6])
    address[0] = (address[0] & 0xFE) | 0x02
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(format_bdaddr(address) + "\n")
    os.chmod(path, 0o600)
    return bytes(address)


def power_on(timeout: float = 90.0) -> None:
    # Samsung's btpower module is loaded asynchronously during the recovery
    # environment's startup, sometimes well after the GNOME session begins.
    deadline = time.monotonic() + timeout
    bluetooth_rfkill = []
    while not bluetooth_rfkill:
        for type_path in Path("/sys/class/rfkill").glob("rfkill*/type"):
            if type_path.read_text().strip() == "bluetooth":
                bluetooth_rfkill.append(type_path.with_name("state"))
        if bluetooth_rfkill:
            break
        if time.monotonic() >= deadline:
            raise FileNotFoundError("Bluetooth rfkill switch is absent")
        time.sleep(0.5)
    # A warm reboot or service restart can leave WCN6850 patched, asleep, and
    # still running at 3.2 Mbit.  Reset its power rail before beginning the
    # ROM protocol at 115200 baud.
    for state_path in bluetooth_rfkill:
        state_path.write_text("0\n")
    time.sleep(0.2)
    for state_path in bluetooth_rfkill:
        state_path.write_text("1\n")
    time.sleep(0.2)


def power_off() -> None:
    for type_path in Path("/sys/class/rfkill").glob("rfkill*/type"):
        if type_path.read_text().strip() == "bluetooth":
            type_path.with_name("state").write_text("0\n")


def attach_qca_ibs(fd: int) -> None:
    fcntl.ioctl(fd, TIOCSETD, struct.pack("i", N_HCI))
    try:
        # The HCI UART line discipline consumes these arguments by value even
        # though the legacy ioctl numbers are declared with _IOW.  Passing a
        # Python buffer therefore sends its userspace address as the flags or
        # protocol number and the kernel correctly rejects it with EINVAL.
        fcntl.ioctl(fd, HCIUARTSETFLAGS, 0)
        fcntl.ioctl(fd, HCIUARTSETPROTO, HCI_UART_QCA)
    except Exception:
        fcntl.ioctl(fd, TIOCSETD, struct.pack("i", N_TTY))
        raise


def attach_h4(fd: int) -> None:
    fcntl.ioctl(fd, TIOCSETD, struct.pack("i", N_HCI))
    try:
        fcntl.ioctl(fd, HCIUARTSETFLAGS, 0)
        fcntl.ioctl(fd, HCIUARTSETPROTO, HCI_UART_H4)
    except Exception:
        fcntl.ioctl(fd, TIOCSETD, struct.pack("i", N_TTY))
        raise


def choose_nvm(directory: Path, board_id: str | None) -> Path:
    if board_id:
        candidate = directory / f"hpnv10.b{board_id}"
        if candidate.exists():
            return candidate
        log(f"board-specific {candidate.name} is absent; using hpnv10.bin")
    return directory / "hpnv10.bin"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--device", default="/dev/ttyHS0")
    parser.add_argument("--firmware-dir", type=Path, required=True)
    parser.add_argument("--xml", type=Path)
    parser.add_argument("--nvm", type=Path)
    parser.add_argument("--bdaddr")
    parser.add_argument(
        "--address-file", type=Path, default=Path("/var/lib/t630-bluetooth/address")
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-attach", action="store_true")
    parser.add_argument("--disable-ibs", action="store_true")
    args = parser.parse_args()

    firmware = (args.firmware_dir / "hpbtfw10.tlv").read_bytes()
    info = firmware_info(firmware)
    bdaddr = parse_bdaddr(args.bdaddr) if args.bdaddr else persistent_address(args.address_file)
    xml_path = args.xml or args.firmware_dir / "bt_nvm_loading.xml"

    if args.dry_run:
        nvm_path = args.nvm or choose_nvm(args.firmware_dir, "18")
        nvm, changed = patch_nvm(
            nvm_path.read_bytes(), xml_path, bdaddr, enable_ibs=not args.disable_ibs
        )
        log(
            f"firmware type={info['type']} size={len(firmware)} mode={info['download_mode']} "
            f"ROM=0x{info['rom_build']:04x} patch=0x{info['patch_version']:04x}"
        )
        log(
            f"validated {nvm_path.name} ({len(nvm)} bytes); changed tags "
            + ",".join(map(str, sorted(changed)))
        )
        log(f"controller address {format_bdaddr(bdaddr)}")
        return 0

    power_on()
    fd = -1
    try:
        fd = os.open(args.device, os.O_RDWR | os.O_NOCTTY)
        configure_uart(fd)
        controller = Controller(fd)
        version = controller.query_version()
        log(
            "controller "
            + " ".join(f"{key}=0x{value:x}" for key, value in version.items())
            + (" unified-HCI" if controller.unified else " legacy-HCI")
        )
        controller.set_high_speed()
        controller.download_tlv(firmware, patch=True)
        board_id = controller.query_board_id()
        nvm_path = args.nvm or choose_nvm(args.firmware_dir, board_id)
        nvm, changed = patch_nvm(
            nvm_path.read_bytes(), xml_path, bdaddr, enable_ibs=not args.disable_ibs
        )
        log(
            f"using {nvm_path.name}, address {format_bdaddr(bdaddr)}, "
            f"patched tags {','.join(map(str, sorted(changed)))}; "
            + (
                "controller IBS disabled for stable H4 transport"
                if args.disable_ibs
                else "controller IBS enabled for the Qualcomm UART transport"
            )
        )
        controller.download_tlv(nvm, patch=False)
        controller.reset()
        log("controller firmware and calibration loaded")
        if args.no_attach:
            return 0
        # The reset command completes before the freshly loaded WCN6850 image
        # has finished initializing its command path.  Attaching immediately
        # lets the HCI core's first command disappear during that window.
        time.sleep(1.0)
        if args.disable_ibs:
            attach_h4(fd)
        else:
            attach_qca_ibs(fd)
        log("hci0 attached; Bluetooth is ready")

        stopped = False

        def stop(_signum, _frame):
            nonlocal stopped
            stopped = True

        signal.signal(signal.SIGTERM, stop)
        signal.signal(signal.SIGINT, stop)
        while not stopped:
            signal.pause()
        fcntl.ioctl(fd, TIOCSETD, struct.pack("i", N_TTY))
        return 0
    except Exception:
        power_off()
        raise
    finally:
        if fd >= 0:
            os.close(fd)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        log(f"ERROR: {error}")
        raise
