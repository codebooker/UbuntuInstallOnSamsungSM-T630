#!/usr/bin/env python3

import importlib.util
import os
import socket
import tempfile
import unittest
from pathlib import Path


TOOLS = Path(__file__).resolve().parent
SPEC = importlib.util.spec_from_file_location("t630_qca_bt", TOOLS / "t630_qca_bt.py")
BT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BT)
FIRMWARE = TOOLS.parent / "reference-bluetooth" / "firmware"
HAS_STOCK_FIRMWARE = all((FIRMWARE / name).is_file() for name in (
    "hpbtfw10.tlv", "hpnv10.b18", "bt_nvm_loading.xml"))


class T630QcaBluetoothTests(unittest.TestCase):
    @unittest.skipUnless(HAS_STOCK_FIRMWARE, "matching stock Bluetooth firmware not extracted")
    def test_firmware_header(self):
        info = BT.firmware_info((FIRMWARE / "hpbtfw10.tlv").read_bytes())
        self.assertEqual(info["type"], 1)
        self.assertEqual(info["download_mode"], 3)
        self.assertEqual(info["rom_build"], 0x0100)

    @unittest.skipUnless(HAS_STOCK_FIRMWARE, "matching stock Bluetooth firmware not extracted")
    def test_nvm_structure(self):
        blob = (FIRMWARE / "hpnv10.b18").read_bytes()
        tags = {tag: length for tag, _, length in BT.iter_nvm_tags(blob)}
        self.assertEqual(tags[2], 6)
        self.assertEqual(tags[17], 6)
        self.assertEqual(tags[35], 120)
        self.assertEqual(tags[50], 232)
        self.assertEqual(tags[87], 80)

    @unittest.skipUnless(HAS_STOCK_FIRMWARE, "matching stock Bluetooth firmware not extracted")
    def test_nvm_patch_is_in_memory_and_complete(self):
        source = (FIRMWARE / "hpnv10.b18").read_bytes()
        address = BT.parse_bdaddr("12:34:56:78:9a:bc")
        result, changed = BT.patch_nvm(
            source, FIRMWARE / "bt_nvm_loading.xml", address, enable_ibs=True
        )
        self.assertEqual((FIRMWARE / "hpnv10.b18").read_bytes(), source)
        self.assertEqual(len(result), len(source))
        self.assertEqual(changed, {2, 17, 27, 35, 36, 50, 83, 85, 87})
        tags = {tag: (start, length) for tag, start, length in BT.iter_nvm_tags(result)}
        start, _ = tags[2]
        self.assertEqual(result[start : start + 6], bytes.fromhex("bc9a78563412"))
        start, _ = tags[17]
        self.assertEqual(result[start] & 0x80, 0x80)
        self.assertEqual(result[start + 1], BT.BAUD_CODE_3200000)
        start, _ = tags[27]
        self.assertEqual(result[start] & 1, 1)
        self.assertEqual(result[start + 1], source[start + 1])
        start, _ = tags[35]
        self.assertEqual([result[start + i] for i in (112, 113, 115, 116)], [11] * 4)
        start, length = tags[87]
        self.assertEqual(length, 80)
        self.assertEqual(result[start : start + 4], bytes([0, 0, 3, 3]))

    @unittest.skipUnless(HAS_STOCK_FIRMWARE, "matching stock Bluetooth firmware not extracted")
    def test_nvm_patch_can_disable_ibs(self):
        source = (FIRMWARE / "hpnv10.b18").read_bytes()
        result, _ = BT.patch_nvm(
            source,
            FIRMWARE / "bt_nvm_loading.xml",
            BT.parse_bdaddr("12:34:56:78:9a:bc"),
            enable_ibs=False,
        )
        tags = {tag: (start, length) for tag, start, length in BT.iter_nvm_tags(result)}
        self.assertEqual(result[tags[17][0]] & 0x80, 0)
        self.assertEqual(result[tags[27][0]] & 1, 0)

    def test_address_validation(self):
        self.assertEqual(BT.format_bdaddr(BT.parse_bdaddr("AA:01:02:03:04:05")),
                         "aa:01:02:03:04:05")
        with self.assertRaises(ValueError):
            BT.parse_bdaddr("not-an-address")

    def test_board_variant_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            firmware = Path(directory)
            for name in ("hpnv10.b18", "hpnv10.b3f", "hpnv10.bin"):
                (firmware / name).touch()
            self.assertEqual(BT.choose_nvm(firmware, "18").name, "hpnv10.b18")
            self.assertEqual(BT.choose_nvm(firmware, "3f").name, "hpnv10.b3f")
            self.assertEqual(BT.choose_nvm(firmware, "ff").name, "hpnv10.bin")

    def test_hci_packets_and_unified_responses(self):
        self.assertEqual(
            BT.hci_command(BT.EDL_PATCH_OPCODE, bytes([BT.EDL_PATCH_VER_REQ])),
            bytes.fromhex("0100fc0119"),
        )
        version = bytearray(21)
        version[0:8] = bytes.fromhex("040e120100fc0019")
        version[9:13] = (0x13).to_bytes(4, "little")
        version[13:15] = (0x44A5).to_bytes(2, "little")
        version[15:17] = (0x0100).to_bytes(2, "little")
        version[17:21] = (0x400C0110).to_bytes(4, "little")
        self.assertTrue(BT.is_unified_version_event(version))
        self.assertEqual(BT.parse_version_event(version, True)["product_id"], 0x13)
        self.assertEqual(BT.parse_version_event(version, True)["soc_id"], 0x400C0110)

        board = bytes.fromhex("040e080100fc0023020018")
        self.assertEqual(BT.parse_board_id(board, True), "18")

    def test_hci_reset_rejects_controller_error(self):
        class FakeController(BT.Controller):
            pass

        original_write = BT._write_all
        original_read = BT.read_event
        try:
            BT._write_all = lambda _fd, _data: None
            BT.read_event = lambda _fd: bytes.fromhex("040e0401030c0c")
            with self.assertRaises(ValueError):
                FakeController(1).reset()
            BT.read_event = lambda _fd: bytes.fromhex("040e0401030c00")
            FakeController(1).reset()
        finally:
            BT._write_all = original_write
            BT.read_event = original_read

    def test_ibs_ack_can_end_the_baud_transition(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, b"\xfc")
            self.assertEqual(BT.read_event(read_fd, allow_ibs_ack=True), b"\xfc")
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_ibs_sleep_can_end_the_baud_transition(self):
        read_fd, write_fd = os.pipe()
        try:
            os.write(write_fd, bytes([BT.HCI_IBS_SLEEP_IND]))
            self.assertEqual(
                BT.read_event(read_fd, allow_ibs_ack=True),
                bytes([BT.HCI_IBS_SLEEP_IND]),
            )
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_qca_attach_uses_value_arguments_for_hci_uart_ioctls(self):
        calls = []
        original_ioctl = BT.fcntl.ioctl
        try:
            BT.fcntl.ioctl = lambda fd, request, arg: calls.append((fd, request, arg))
            BT.attach_qca_ibs(9)
        finally:
            BT.fcntl.ioctl = original_ioctl

        self.assertEqual(calls[0][0:2], (9, BT.TIOCSETD))
        self.assertIsInstance(calls[0][2], bytes)
        self.assertEqual(calls[1], (9, BT.HCIUARTSETFLAGS, 0))
        self.assertEqual(calls[2], (9, BT.HCIUARTSETPROTO, BT.HCI_UART_QCA))

    def test_h4_attach_uses_value_arguments_for_hci_uart_ioctls(self):
        calls = []
        original_ioctl = BT.fcntl.ioctl
        try:
            BT.fcntl.ioctl = lambda fd, request, arg: calls.append((fd, request, arg))
            BT.attach_h4(9)
        finally:
            BT.fcntl.ioctl = original_ioctl

        self.assertEqual(calls[1], (9, BT.HCIUARTSETFLAGS, 0))
        self.assertEqual(calls[2], (9, BT.HCIUARTSETPROTO, BT.HCI_UART_H4))

    def test_dry_run_does_not_need_hardware(self):
        with tempfile.TemporaryDirectory() as directory:
            address_file = Path(directory) / "address"
            address = BT.persistent_address(address_file)
            self.assertEqual(address, BT.persistent_address(address_file))
            self.assertTrue(address[0] & 0x02)
            self.assertFalse(address[0] & 0x01)

    def test_ibs_wake_handshake(self):
        host, controller = socket.socketpair()
        try:
            controller.send(bytes([BT.HCI_IBS_WAKE_ACK]))
            BT.wake_controller(host.fileno())
            self.assertEqual(controller.recv(1), bytes([BT.HCI_IBS_WAKE_IND]))
        finally:
            host.close()
            controller.close()


if __name__ == "__main__":
    unittest.main()
