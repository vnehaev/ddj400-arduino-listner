#!/usr/bin/env python3
from __future__ import annotations

import json
import logging
import os
import socket
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

try:
    import serial
    from serial.tools import list_ports
except ImportError:
    serial = None
    list_ports = None

try:
    from smbus2 import SMBus
except ImportError:
    SMBus = None

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(levelname)s %(message)s",
)
logger = logging.getLogger("display-bridge")

UDP_HOST = os.getenv("UDP_HOST", "127.0.0.1")
UDP_PORT = int(os.getenv("UDP_PORT", "5005"))
REFRESH_INTERVAL = float(os.getenv("REFRESH_INTERVAL", "0.20"))
REDISCOVERY_INTERVAL = float(os.getenv("REDISCOVERY_INTERVAL", "3.0"))
PREFERRED_OUTPUT = os.getenv("PREFERRED_OUTPUT", "auto").strip().lower()
OLED_I2C_PORT = int(os.getenv("OLED_I2C_PORT", "1"))
OLED_I2C_ADDRESSES = [0x3C, 0x3D]
SERIAL_BAUDRATE = int(os.getenv("SERIAL_BAUDRATE", "115200"))
MAX_LINE_LENGTH = int(os.getenv("MAX_LINE_LENGTH", "21"))


@dataclass
class DeckState:
    bpm: float = 0.0
    playing: bool = False
    elapsed: str = "--:--"
    title: str = ""


class BaseBackend:
    name = "base"

    def render(self, lines: list[str]) -> None:
        raise NotImplementedError

    def close(self) -> None:
        pass


class ConsoleBackend(BaseBackend):
    name = "console"

    def render(self, lines: list[str]) -> None:
        logger.info("\n%s", "\n".join(lines))


class RaspberryOledBackend(BaseBackend):
    name = "raspberry_oled"

    def __init__(self, address: int) -> None:
        from luma.core.interface.serial import i2c
        from luma.oled.device import ssd1306
        from PIL import Image, ImageDraw, ImageFont

        self._Image = Image
        self._ImageDraw = ImageDraw
        self._font = ImageFont.load_default()
        self._serial = i2c(port=OLED_I2C_PORT, address=address)
        self._device = ssd1306(self._serial)
        self._address = address
        logger.info("Using local OLED on Raspberry Pi, address=0x%02X", address)

    def render(self, lines: list[str]) -> None:
        image = self._Image.new("1", (self._device.width, self._device.height))
        draw = self._ImageDraw.Draw(image)
        draw.rectangle((0, 0, self._device.width, self._device.height), outline=0, fill=0)

        if self._device.height <= 32:
            lines = lines[:2]
            y_step = 16
        else:
            lines = lines[:4]
            y_step = 16

        for index, line in enumerate(lines):
            draw.text((0, index * y_step), line, font=self._font, fill=255)

        self._device.display(image)

    def close(self) -> None:
        try:
            self._device.clear()
        except Exception:
            pass


class ArduinoSerialBackend(BaseBackend):
    name = "arduino_serial"

    def __init__(self, port: str) -> None:
        if serial is None:
            raise RuntimeError("pyserial is not installed")

        self._serial = serial.Serial(
            port=port,
            baudrate=SERIAL_BAUDRATE,
            timeout=1,
            write_timeout=1,
        )
        self._port = port
        time.sleep(2.0)
        self._serial.reset_input_buffer()
        self._serial.reset_output_buffer()
        self._serial.write(b"PING\n")
        self._serial.flush()
        reply = self._serial.readline().decode("utf-8", errors="ignore").strip()
        if not reply.startswith("PONG"):
            self._serial.close()
            raise RuntimeError(f"Handshake failed on {port}: {reply!r}")
        logger.info("Using Arduino display receiver on %s", port)

    @staticmethod
    def _sanitize(value: str) -> str:
        return value.replace("|", "/").replace("\n", " ").strip()

    def render(self, lines: list[str]) -> None:
        normalized = [self._sanitize(line) for line in lines[:4]]
        while len(normalized) < 4:
            normalized.append("")
        payload = "SCREEN|" + "|".join(normalized) + "\n"
        self._serial.write(payload.encode("utf-8"))
        self._serial.flush()

    def close(self) -> None:
        try:
            self._serial.close()
        except Exception:
            pass


def trim_text(value: str, max_len: int = MAX_LINE_LENGTH) -> str:
    value = (value or "").strip()
    if len(value) <= max_len:
        return value.ljust(max_len)
    return value[: max_len - 1] + "…"


def scan_local_oled_address() -> Optional[int]:
    if SMBus is None:
        logger.debug("smbus2 is not installed, skipping local OLED detection")
        return None

    i2c_path = Path(f"/dev/i2c-{OLED_I2C_PORT}")
    if not i2c_path.exists():
        logger.debug("%s not found, skipping local OLED detection", i2c_path)
        return None

    try:
        with SMBus(OLED_I2C_PORT) as bus:
            for address in OLED_I2C_ADDRESSES:
                try:
                    bus.read_byte(address)
                    return address
                except OSError:
                    continue
    except Exception as exc:
        logger.warning("Could not scan I2C bus: %s", exc)

    return None


def list_candidate_serial_ports() -> list[str]:
    if list_ports is None:
        logger.debug("pyserial is not installed, skipping Arduino detection")
        return []

    candidates: list[str] = []
    keywords = ("arduino", "ch340", "usb serial", "cp210", "ttyacm", "ttyusb")

    for port in list_ports.comports():
        haystack = " ".join(
            filter(None, [port.device, port.description, port.manufacturer or ""])
        ).lower()
        if any(keyword in haystack for keyword in keywords):
            candidates.append(port.device)

    for fallback in sorted({*candidates, "/dev/ttyACM0", "/dev/ttyUSB0"}):
        if os.path.exists(fallback) and fallback not in candidates:
            candidates.append(fallback)

    return candidates


def detect_backend() -> Optional[BaseBackend]:
    detection_order = [PREFERRED_OUTPUT] if PREFERRED_OUTPUT in {"raspberry", "arduino"} else ["raspberry", "arduino"]

    for output_type in detection_order:
        if output_type == "raspberry":
            address = scan_local_oled_address()
            if address is None:
                continue
            try:
                return RaspberryOledBackend(address)
            except Exception as exc:
                logger.warning("Local OLED detected but backend init failed: %s", exc)

        if output_type == "arduino":
            for port in list_candidate_serial_ports():
                try:
                    return ArduinoSerialBackend(port)
                except Exception as exc:
                    logger.debug("Serial backend rejected %s: %s", port, exc)

    return None


class UnifiedDisplayBridge:
    def __init__(self) -> None:
        self.decks = {1: DeckState(), 2: DeckState()}
        self.lock = threading.Lock()
        self.running = True
        self.backend: Optional[BaseBackend] = None
        self.last_detection_attempt = 0.0
        self.last_render_signature: Optional[tuple[str, ...]] = None

    def update_deck(self, payload: dict) -> None:
        deck = int(payload.get("deck", 0))
        if deck not in self.decks:
            return

        with self.lock:
            state = self.decks[deck]
            bpm = payload.get("bpm")
            if bpm is not None:
                try:
                    state.bpm = float(bpm)
                except (TypeError, ValueError):
                    pass

            if "playing" in payload:
                state.playing = bool(payload["playing"])

            if payload.get("elapsed") is not None:
                state.elapsed = str(payload["elapsed"])

            if payload.get("title") is not None:
                state.title = str(payload["title"])

    def build_lines(self) -> list[str]:
        with self.lock:
            d1 = self.decks[1]
            d2 = self.decks[2]

        def header(deck_no: int, state: DeckState) -> str:
            status = ">" if state.playing else "||"
            bpm = f"{state.bpm:5.1f}" if state.bpm > 0 else "  --.-"
            elapsed = trim_text(state.elapsed, max_len=5).strip() or "--:--"
            return trim_text(f"D{deck_no} {status} {bpm} {elapsed}")

        return [
            header(1, d1),
            trim_text(d1.title or "Deck 1"),
            header(2, d2),
            trim_text(d2.title or "Deck 2"),
        ]

    def serve_udp(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_HOST, UDP_PORT))
        logger.info("Listening for updates on %s:%s", UDP_HOST, UDP_PORT)

        while self.running:
            data, _ = sock.recvfrom(4096)
            try:
                payload = json.loads(data.decode("utf-8"))
                self.update_deck(payload)
            except Exception as exc:
                logger.warning("Bad UDP packet ignored: %s", exc)

    def ensure_backend(self) -> None:
        now = time.monotonic()
        if self.backend is not None:
            return
        if now - self.last_detection_attempt < REDISCOVERY_INTERVAL:
            return

        self.last_detection_attempt = now
        self.backend = detect_backend()
        if self.backend is None:
            logger.warning("No display backend detected yet")

    def render_loop(self) -> None:
        while self.running:
            self.ensure_backend()
            lines = self.build_lines()
            signature = tuple(lines)

            if self.backend is not None and signature != self.last_render_signature:
                try:
                    self.backend.render(lines)
                    self.last_render_signature = signature
                except Exception as exc:
                    logger.error("Backend %s failed: %s", self.backend.name, exc)
                    try:
                        self.backend.close()
                    finally:
                        self.backend = None
                        self.last_render_signature = None

            time.sleep(REFRESH_INTERVAL)

    def run(self) -> None:
        udp_thread = threading.Thread(target=self.serve_udp, daemon=True)
        udp_thread.start()

        try:
            self.render_loop()
        except KeyboardInterrupt:
            logger.info("Stopping bridge")
        finally:
            self.running = False
            if self.backend is not None:
                self.backend.close()


if __name__ == "__main__":
    UnifiedDisplayBridge().run()
